import copy
import json

from typing import Union, List, Any
from chainpy.eth.ethtype.account import EthAccount
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.chaindata import EthReceipt
from bridgeconst.consts import Chain, Asset, RBCMethodDirection
from bridgeconst.testbridgespec import SUPPORTING_ASSETS
from chainpy.eth.ethtype.hexbytes import EthAddress
from chainpy.eth.managers.multichainmanager import MultiChainManager
from relayer.relayer import Relayer
from relayer.tools.consts import ADMIN_RELAYERS, USER_CONFIG_PATH, PRIVATE_CONFIG_PATH
from relayer.user import User

KEY_JSON_PATH = "./configs/keys.json"


class Manager(User, Relayer):
    def __init__(self, multichain_config: dict):
        super().__init__(multichain_config)

    @classmethod
    def init_manager(cls, role: str, project_root_path: str = "./", account: EthAccount = None):
        manager = Manager.from_config_files(USER_CONFIG_PATH, PRIVATE_CONFIG_PATH)

        with open(project_root_path + KEY_JSON_PATH) as f:
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
    for chain_index in manager.supported_chain_list:
        display_multichain_balances_on(manager, chain_index, target_addr, no_print_title=True, coin_only=True)


def display_multichain_asset_balances(manager: Manager, addr: EthAddress = None):
    target_addr = manager.active_account.address if addr is None else addr
    print("\n<Multi-chain asset balances>\n - {}".format(target_addr.hex()))
    for chain_index in manager.supported_chain_list:
        display_multichain_balances_on(manager, chain_index, target_addr, no_print_title=True, coin_only=False)


def display_multichain_balances_on(
        manager: Manager, chain_index: Chain,
        addr: EthAddress = None, no_print_title: bool = False, coin_only: bool = False):
    target_addr = manager.active_account.address if addr is None else addr
    if not no_print_title:
        print("\n<{} balances on {}>".format(target_addr.hex(), chain_index))

    print(chain_index.name + "-" * (BALANCE_FORMAT_STRING_LEN * INLINE_BALANCES_NUM + 1 - len(chain_index.name)))
    bal_str, bal_num = "", 0
    target_asset_list = asset_list_of(chain_index)
    for token in target_asset_list:
        if token.is_coin():
            bal = manager.world_native_balance(chain_index, target_addr)
        else:
            if coin_only:
                continue
            bal = manager.world_token_balance_of(chain_index, token, target_addr)
        balance_str = "> 1M" if bal > EthAmount(1000000.0) else bal.change_decimal(2).float_str
        bal_str += BALANCE_FORMAT.format(token.symbol, balance_str)
        bal_num += 1
        if bal_num % INLINE_BALANCES_NUM == 0:
            print(bal_str + "|")
            bal_str = ""
    if bal_str != "":
        print(bal_str + "|")
    print("-" * (BALANCE_FORMAT_STRING_LEN * INLINE_BALANCES_NUM + 1))


def display_receipt_status(receipt: EthReceipt):
    if receipt is None:
        msg = "None-receipt"
    else:
        msg = "tx({}) ".format(receipt.transaction_hash.hex())
        msg += "successes" if receipt.status == 1 else "fails"
    print(msg)


def get_typed_item_from_console(prompt: str, item_type: type) -> Any:
    input_str = input(">>> " + prompt + ": ")
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
        supported_chain_list_clone.remove(Chain.BFC_TEST)

    prompt = "select a chain"
    chain_index = get_option_from_console(prompt, supported_chain_list_clone)
    return chain_index


def get_asset_from_console(chain_index: Chain = None, token_only: bool = False) -> Asset:
    prompt = "select a asset"
    asset_options = asset_list_of(chain_index, token_only)

    if not asset_options:
        return Asset.NONE
    else:
        return get_option_from_console(prompt, asset_options)


def get_chain_and_asset_from_console_for_bridge(
        manager: MultiChainManager,
        direction: RBCMethodDirection,
        token_only: bool = False,
        not_included_bifrost: bool = False) -> (Chain, Asset):
    chain_index = get_chain_from_console(manager, not_included_bifrost)

    if direction == RBCMethodDirection.INBOUND:
        token_index = get_asset_from_console(chain_index, token_only)
    else:
        token_index = get_asset_from_console(Chain.BFC_TEST, token_only)
    return chain_index, token_index


def get_chain_and_asset_from_console(
        manager: MultiChainManager,
        token_only: bool = False) -> (Chain, Asset):
    chain_index = get_chain_from_console(manager)
    token_index = get_asset_from_console(chain_index, token_only)
    return chain_index, token_index


def asset_list_of(chain: Chain = None, token_only: bool = False) -> List[Asset]:
    if chain is None:
        return SUPPORTING_ASSETS

    coins, tokens = [], []
    for asset in SUPPORTING_ASSETS:
        if asset.chain == chain:
            if asset.is_coin():
                coins.append(asset)
            else:
                tokens.append(asset)
    return tokens if token_only else coins + tokens


def fetch_and_display_rounds(manager: Union[User, Relayer]):
    print("-----------------------------------------------")
    for chain_index in manager.supported_chain_list:
        _round = manager.world_call(chain_index, "relayer_authority", "latest_round", [])[0]
        print("{:>8}: {}".format(chain_index.name, _round))
    print("-----------------------------------------------")
