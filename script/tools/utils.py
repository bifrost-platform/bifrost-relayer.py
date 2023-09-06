import copy
import json
import time
from typing import Union, List, Any, Tuple

from bridgeconst.consts import Chain, Asset, Symbol, RBCMethodV1, AssetType
from bridgeconst.mainbridgespec import SUPPORTING_ASSETS as MAINNET_ASSETS
from bridgeconst.testbridgespec import SUPPORTING_ASSETS as TESTNET_ASSETS
from chainpy.eth.ethtype.account import EthAccount
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.hexbytes import EthAddress
from chainpy.eth.ethtype.receipt import EthReceipt
from chainpy.eth.managers.multichainmanager import MultiChainManager

from rbclib.primitives.relay_asset import asset_enum
from rbclib.primitives.relay_chain import chain_enum
from relayer.relayer import Relayer
from relayer.user import User
from relayer.user_utils import symbol_to_asset
from script.tools.consts import (
    USER_MAINNET_CONFIG_PATH,
    USER_TESTNET_CONFIG_PATH,
    PRIVATE_MAINNET_CONFIG_PATH,
    PRIVATE_TESTNET_CONFIG_PATH,
    KEY_JSON_PATH
)


class Manager(User, Relayer):
    def __init__(self, multichain_config: dict):
        super().__init__(multichain_config)

    @classmethod
    def init_manager(cls, role: str, is_testnet: bool, account: EthAccount = None):
        if is_testnet:
            chain_enum.switch_testnet_config()
            asset_enum.switch_testnet_config()
            manager = Manager.from_config_files(USER_TESTNET_CONFIG_PATH, PRIVATE_TESTNET_CONFIG_PATH)
        else:
            manager = Manager.from_config_files(USER_MAINNET_CONFIG_PATH, PRIVATE_MAINNET_CONFIG_PATH)

        with open(KEY_JSON_PATH) as f:
            key = json.load(f)[role.lower()]
        manager.set_account(key)

        if account is not None:
            manager.set_account(hex(account.priv))

        return manager


TOKEN_NAME_LEN = 5
BALANCE_STRING_LEN = 9
BALANCE_FORMAT = "|{:>" + str(TOKEN_NAME_LEN) + "}: {:>" + str(BALANCE_STRING_LEN) + "} "
BALANCE_FORMAT_STRING_LEN = TOKEN_NAME_LEN + BALANCE_STRING_LEN + 4
INLINE_BALANCES_NUM = 3


def display_multichain_coins_balances(manager: Manager, addr: EthAddress = None):
    target_addr = manager.active_account.address if addr is None else addr
    print("\n<Multi-chain coin balances>\n - {}".format(target_addr.hex()))
    for chain_name in manager.supported_chain_list:
        chain = Chain[chain_name]
        display_multichain_balances_on(manager, chain, target_addr, no_print_title=True, coin_only=True)


def display_multichain_asset_balances(manager: Manager, addr: EthAddress = None):
    target_addr = manager.active_account.address if addr is None else addr
    print("\n<Multi-chain asset balances>\n - {}".format(target_addr.hex()))
    for chain_name in manager.supported_chain_list:
        chain = Chain[chain_name]
        display_multichain_balances_on(manager, chain, target_addr, no_print_title=True, coin_only=False)


def display_multichain_balances_on(
    manager: Manager, chain: Chain,
    addr: EthAddress = None, no_print_title: bool = False, coin_only: bool = False):
    target_addr = manager.active_account.address if addr is None else addr
    if not no_print_title:
        print("\n<{} balances on {}>".format(target_addr.hex(), chain))

    print(chain.name + "-" * (BALANCE_FORMAT_STRING_LEN * INLINE_BALANCES_NUM + 1 - len(chain.name)))
    bal_str, bal_num = "", 0
    target_asset_list = asset_list_on(chain)
    for asset in target_asset_list:
        if not asset.is_coin() and coin_only:
            continue
        bal = manager.world_balance(chain.name, asset=asset, user_addr=target_addr)
        balance_str = "> 1M" if bal > EthAmount(1000000.0) else bal.change_decimal(2).float_str
        bal_str += BALANCE_FORMAT.format(asset.symbol, balance_str)
        bal_num += 1
        if bal_num % INLINE_BALANCES_NUM == 0:
            print(bal_str + "|")
            bal_str = ""
    if bal_str != "":
        print(bal_str + "|")
    print("-" * (BALANCE_FORMAT_STRING_LEN * INLINE_BALANCES_NUM + 1))


def display_receipt_status(receipt: EthReceipt):
    if receipt is None:
        msg = ">>> None-receipt"
    else:
        msg = ">>> tx({}) ".format(receipt.transaction_hash.hex())
        msg += "successes" if receipt.status == 1 else "fails"
    print(msg)


def get_typed_item_from_console(prompt: str, item_type: type) -> Any:
    input_str = input("\n>>> " + prompt + ": ")
    input_obj = item_type(input_str) if input_str != "" else None
    print(">>> {}: [{}]".format("selected item", input_obj))
    return input_obj


def get_option_from_console(prompt: str, options: List) -> Any:
    # build prompt message
    prompt_str = ""
    for i, option in enumerate(options):
        prompt_str += "\n{:>2}: {}".format(i + 1, str(option))
    prompt_str += "\n<<< {}: ".format(prompt)

    # request insert integer as a command
    inserted_cmd = int(input(prompt_str))
    if len(options) < inserted_cmd:
        raise Exception("should select 1 to {}".format(len(options)))

    selected_option = options[inserted_cmd - 1]
    print(">>> selected option: [{}]".format(selected_option))
    return selected_option


def get_chain_from_console(manager: MultiChainManager, not_included_bifrost: bool = False) -> Chain:
    # remove BIFROST from the supported chain list
    supported_chain_list_clone = copy.deepcopy(manager.supported_chain_list)
    if not_included_bifrost:
        supported_chain_list_clone.remove(chain_enum.BIFROST.name)

    prompt = "select a chain"
    chain_name = get_option_from_console(prompt, supported_chain_list_clone)
    return Chain.from_name(chain_name)


def asset_list_on(chain: Chain = None, token_only: bool = False, is_testnet: bool = False) -> List[Asset]:
    if chain is None and is_testnet is None:
        raise Exception("You must enter chain or is_testnet to specify the network.")

    if chain is not None:
        is_testnet = chain.name.split("_")[1] != "MAIN"

    supporting_asset = TESTNET_ASSETS if is_testnet else MAINNET_ASSETS

    if chain is None:
        return supporting_asset

    coins, tokens = [], []
    for asset in supporting_asset:
        if asset.chain == chain:
            if asset.asset_type == AssetType.BRIDGED:
                continue
            if asset.asset_type == AssetType.UNIFIED and asset.symbol == Symbol.BFC:
                continue
            if asset.is_coin():
                coins.append(asset)
            else:
                tokens.append(asset)
    return tokens if token_only else coins + tokens


def symbol_list_on(chain: Chain = None, token_only: bool = False, is_testnet: bool = False) -> List[Symbol]:
    asset_list = asset_list_on(chain, token_only=token_only, is_testnet=is_testnet)
    return list(set([asset.symbol for asset in asset_list]))


def get_symbol_from_console(chain: Chain = None, token_only: bool = False) -> Symbol:
    prompt = "select a symbol of asset"
    symbol_options = symbol_list_on(chain, token_only)
    return get_option_from_console(prompt, symbol_options)


def get_asset_from_console(chain: Chain = None, token_only: bool = False) -> Asset:
    symbol = get_symbol_from_console(chain, token_only=token_only)
    return symbol_to_asset(chain, symbol)


def get_chain_and_symbol_from_console(
    manager: MultiChainManager,
    token_only: bool = False,
    not_included_bifrost: bool = False) -> Tuple[Chain, Symbol]:
    chain = get_chain_from_console(manager, not_included_bifrost)
    symbol = get_symbol_from_console(chain, token_only)
    return chain, symbol


def fetch_and_display_rounds(manager: Union[User, Relayer]):
    print("-----------------------------------------------")
    for chain_name in manager.supported_chain_list:
        _round = manager.world_call(chain_name, "relayer_authority", "latest_round", [])[0]
        print("{:>8}: {}".format(chain_name, _round))
    print("-----------------------------------------------")


def fetch_asset_config(manager: Union[User, Relayer], asset: Asset, chain: Chain):
    return manager.world_call(chain.name, "vault", "assets_config", [asset.formatted_bytes()])


def fetch_bridge_amount_config(
    manager: Union[User, Relayer], asset: Asset, src_chain: Chain, dst_chain: Chain
) -> Tuple[EthAmount, EthAmount, EthAmount]:
    if asset.asset_type == AssetType.UNIFIED:
        asset = Asset.from_name("BRIDGED_{}_{}_ON_{}".format(dst_chain.name, asset.symbol.name, src_chain.name))

    decimal = asset.decimal
    config = manager.world_call(src_chain.name, "vault", "assets_config", [asset.formatted_bytes()])
    return EthAmount(config[1][0], decimal), EthAmount(config[1][1], decimal), EthAmount(config[1][2], decimal)


def fetch_bridge_fee_config(
    manager: Union[User, Relayer], chain: Chain, asset: Asset) -> Tuple[EthAmount, EthAmount, EthAmount]:
    decimal = asset.decimal
    config = manager.world_call(chain.name, "vault", "assets_config", [asset.formatted_bytes()])
    return EthAmount(config[0][0], decimal), EthAmount(config[0][1], decimal), EthAmount(config[0][2], decimal)


def display_addrs(title: str, addrs: List[str]):
    print("<{}>".format(title))
    for addr in addrs:
        print("  - {}".format(addr))


def cccp_batch_send(
    user: Manager,
    batch_num: int,
    src_chain: Chain,
    dst_chain: Chain,
    symbol: Symbol,
    rbc_method: RBCMethodV1,
    amount: EthAmount
) -> Tuple[List[EthReceipt], List[Tuple[Chain, int, int]]]:
    request_txs = list()
    print(">>> build transaction for each request")
    for _ in range(batch_num):
        tx = user.build_cross_action_tx(src_chain, dst_chain, symbol, rbc_method, amount)
        request_txs.append(tx)
    print(">>>> complete")

    tx_hashes = list()
    print("\n>>> send transaction for each request")
    for i in range(batch_num):
        tx_hash = user.world_send_transaction(src_chain.name, request_txs[i])
        tx_hashes.append(tx_hash)
    print(">>>> completes, sleep 30 sec")
    time.sleep(30)

    receipts = list()
    rids = list()

    print("\n>>> start check receipt for each request")
    for i in range(batch_num):
        receipt = user.world_receipt_with_wait(src_chain.name, tx_hashes[i])
        result = user.get_contract_obj_on(src_chain.name, "socket"). \
            get_method_abi("Socket"). \
            decode_event_data(receipt.logs[3].data)[0]
        receipts.append(receipt)
        rids.append((Chain.from_bytes(result[0][0]), result[0][1], result[0][2]))
    print(">>>> completes")

    return receipts, rids
