import copy
import json
import unittest

from typing import Union, List, Any, Optional

from relayer.chainpy.eth.ethtype.account import EthAccount
from relayer.chainpy.eth.ethtype.chaindata import EthReceipt
from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthAddress
from relayer.chainpy.eth.managers.configs import EntityRootConfig
from relayer.chainpy.eth.managers.multichainmanager import MultiChainManager
from relayer.rbcevents.consts import TokenStreamIndex
from relayer.relayer import Relayer
from relayer.tools.consts import ADMIN_RELAYERS, USER_CONFIG_PATH, PRIVATE_CONFIG_PATH, SUPPORTED_TOKEN_LIST
from relayer.user import User

KEY_JSON_PATH = "./relayer/tools/keys.json"


def _parse_key(project_root_path: str, key_json_path: str, role: str) -> str:
    with open(project_root_path + key_json_path) as f:
        key = json.load(f)[role.lower()]
    return str(key)


def init_manager(role: str, project_root_path: str = "./", account: EthAccount = None) -> Union[User, Relayer]:
    config = EntityRootConfig.from_config_files(USER_CONFIG_PATH, PRIVATE_CONFIG_PATH, project_root_path)
    config.entity.secret_hex = _parse_key(project_root_path, KEY_JSON_PATH, role)

    if account is not None:
        config.entity.secret_hex = hex(account.priv)

    if role.lower() == "operator":
        return Relayer(config)
    else:
        # for admin, nominator, recharger
        return User(config)


def is_admin_relayer(addr: Union[str, EthAddress]):
    if isinstance(addr, str):
        addr = EthAddress(addr)
    return addr.hex().lower() in ADMIN_RELAYERS


def remove_duplicated_addr(addrs: List[EthAddress]) -> List[EthAddress]:
    if len(addrs) == 0:
        return []
    if isinstance(addrs[0], str):
        addrs = [EthAddress(addr) for addr in addrs]
    ret_addrs = list()
    for addr in addrs:
        if addr not in ret_addrs:
            ret_addrs.append(addr)
    return ret_addrs


def remove_addresses_from(addrs: List[EthAddress], to_remove_addrs: List[EthAddress]):
    input_addrs = [addr.hex().lower() for addr in addrs]
    ret = list()
    for addr_hex in input_addrs:
        if addr_hex not in [addr.hex().lower() for addr in to_remove_addrs]:
            ret.append(EthAddress(addr_hex))
    return ret


def remove_admin_addresses_from(addrs: List[EthAddress]) -> List[EthAddress]:
    return remove_addresses_from(addrs, [EthAddress(addr) for addr in ADMIN_RELAYERS])


def display_addrs(
        title: str,
        addrs: List[EthAddress],
        auxiliary_addrs: List[EthAddress] = None,
        auxiliary_ints: List[int] = None,
        auxiliary_strs: List[str] = None):

    print(title)
    print("-----------------------------------------------------" * 2)
    for i, addr in enumerate(addrs):
        msg = "{:>2}: {}".format(i + 1, addr.hex().lower())
        if auxiliary_addrs is not None:
            msg += " {}".format(auxiliary_addrs[i].hex().lower())
        if auxiliary_ints is not None:
            msg += " {}".format(str(auxiliary_ints[i] // 10 ** 18))
        if auxiliary_strs is not None:
            msg += " {}".format(auxiliary_strs[i])
        print(msg)
    print("-----------------------------------------------------" * 2)


def display_coins_balances(manager: MultiChainManager, addr: EthAddress = None):
    print("\n<{} balances>".format(manager.active_account.address.hex()))
    print("-------------------------------" * len(manager.supported_chain_list))
    bal_str = ""
    for chain_index in manager.supported_chain_list:
        bal = manager.world_native_balance(chain_index, addr)
        bal_str += "|{:>8}: {:>17}, ".format(chain_index.name, bal.change_decimal(2).float_str)
    print(bal_str[:-2])
    print("-------------------------------" * len(manager.supported_chain_list))


def display_asset_balances_on_chain(
        manager: Union[User, Relayer], chain_index: ChainIndex,
        addr: EthAddress = None, no_print: bool = False) -> Optional[str]:
    target_addr = manager.active_account.address if addr is None else addr
    if not no_print:
        print("\n<{} balances on {}>".format(target_addr.hex(), chain_index))
    balance_cache = list()
    target_asset_list = asset_list_of(chain_index)
    for token in target_asset_list:
        if token.is_coin_on(chain_index):
            bal = manager.world_native_balance(chain_index, target_addr)
        else:
            bal = manager.world_token_balance_of(chain_index, token, target_addr)
        balance_cache.append([token, bal])

    bal_str, bal_num = "", 0
    for item in balance_cache:
        token, bal = item[0], item[1]
        bal_str += "|{:>5}: {:>13}, ".format(token.token_name(), bal.change_decimal(2).float_str)
        bal_num += 1
        if bal_num % 3 == 0:
            bal_str = bal_str[:-2] + "\n"
    if not no_print:
        print("-----------------------" * 3)
        print(bal_str[:-2])
        print("-----------------------" * 3)
    else:
        return bal_str[:-2]


def display_multichain_asset_balances(manager: Union[User, Relayer], addr: EthAddress = None):
    target_addr = manager.active_account.address if addr is None else addr
    print("\n<{} balances on {}>".format(target_addr.hex(), "multi-chain"))
    print("-----------------------" * 3)
    for chain_index in manager.supported_chain_list:
        bal_str = display_asset_balances_on_chain(manager, chain_index, addr, True)
        print(bal_str)
        print("-----------------------" * 3)


def display_receipt_status(receipt: EthReceipt):
    if receipt is None:
        msg = "None-receipt"
    else:
        msg = "tx({}) ".format(receipt.transaction_hash.hex())
        msg += "successes" if receipt.status == 1 else "fails"
    print(msg)


# not tested
def get_typed_item_from_console(prompt: str, item_type: type) -> Any:
    input_str = input(">>> " + prompt + ": ")
    input_obj = item_type(input_str) if input_str != "" else None
    print(">>> {}: [{}]".format("selected item", input_obj))
    return input_obj


# not tested
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


# not tested
def get_chain_index_from_console(manager: MultiChainManager, not_included_bifrost: bool = False) -> ChainIndex:
    # remove BIFROST from the supported chain list
    supported_chain_list_clone = copy.deepcopy(manager.supported_chain_list)
    if not_included_bifrost:
        supported_chain_list_clone.remove(ChainIndex.BIFROST)

    prompt = "select a chain"
    chain_index = get_option_from_console(prompt, supported_chain_list_clone)
    return chain_index


# not tested
def get_token_index_from_console(chain_index: ChainIndex = None, token_only: bool = False) -> TokenStreamIndex:
    prompt = "select chain index number"
    token_options = asset_list_of(chain_index)

    options = []
    if token_only:
        for opt in token_options:
            if not opt.is_coin_on(chain_index):
                options.append(opt)
    else:
        options = token_options

    if not options:
        return TokenStreamIndex.NONE
    else:
        return get_option_from_console(prompt, options)


# not tested
def get_chain_and_token(
        manager: MultiChainManager,
        token_only: bool = False,
        not_included_bifrost: bool = False) -> (ChainIndex, TokenStreamIndex):
    chain_index = get_chain_index_from_console(manager, not_included_bifrost)
    token_index = get_token_index_from_console(chain_index, token_only)
    return chain_index, token_index


# not tested
def asset_list_of(chain_index: ChainIndex = None):
    ret = []
    if chain_index is None or chain_index == ChainIndex.BIFROST:
        return SUPPORTED_TOKEN_LIST

    for token_stream_index in SUPPORTED_TOKEN_LIST:
        if token_stream_index.home_chain_index() == chain_index:
            ret.append(token_stream_index)
        if chain_index == ChainIndex.ETHEREUM and token_stream_index == TokenStreamIndex.BFC_BIFROST:
            ret.append(token_stream_index)
    return ret


# not tested
def determine_decimal(token_index: TokenStreamIndex) -> int:
    return 6 if token_index == TokenStreamIndex.USDT_ETHEREUM or token_index == TokenStreamIndex.USDC_ETHEREUM else 18


class TestUtil(unittest.TestCase):
    def setUp(self) -> None:
        self.user = init_manager("user", "../../")
        self.admin = init_manager("admin", "../../")
        self.admin_addr = EthAddress("0x72da8d1d9ca516f074e1bcac413bbc4d12ad7ca0")

    def test_user_obj(self):
        self.assertIn(ChainIndex.BIFROST, self.user.supported_chain_list)
        self.assertIn(ChainIndex.ETHEREUM, self.user.supported_chain_list)
        self.assertIn(ChainIndex.POLYGON, self.user.supported_chain_list)
        self.assertIn(ChainIndex.BINANCE, self.user.supported_chain_list)
        self.assertEqual(self.user.active_account.address, "0x466D25b791FD4882e15aF01FC28a633014104B2b")

        self.assertIn(ChainIndex.BIFROST, self.admin.supported_chain_list)
        self.assertIn(ChainIndex.ETHEREUM, self.admin.supported_chain_list)
        self.assertIn(ChainIndex.POLYGON, self.admin.supported_chain_list)
        self.assertIn(ChainIndex.BINANCE, self.admin.supported_chain_list)
        self.assertEqual(self.admin.active_account.address, "0x5D129e8792B5341b51c36F689Db8De6200E69f7d")

    def test_display_balance(self):
        display_coins_balances(self.user, self.user.active_account.address)
        display_asset_balances_on_chain(self.user, ChainIndex.BIFROST, self.user.active_account.address)
        display_multichain_asset_balances(self.user, self.user.active_account.address)

    def test_addr_util(self):
        test_addr_list = [
            EthAddress("0x1000000000000000000000000000000000000000"),
            EthAddress("0x2000000000000000000000000000000000000000"),
            EthAddress("0x1000000000000000000000000000000000000000"),
            EthAddress("0x3000000000000000000000000000000000000000"),
            self.admin_addr
        ]

        expected_remove_duplicated_addr_list = [
            EthAddress("0x1000000000000000000000000000000000000000"),
            EthAddress("0x2000000000000000000000000000000000000000"),
            EthAddress("0x3000000000000000000000000000000000000000"),
            self.admin_addr
        ]
        result_remove_duplicated = remove_duplicated_addr(test_addr_list)
        self.assertNotEqual(test_addr_list, result_remove_duplicated)
        self.assertEqual(expected_remove_duplicated_addr_list, result_remove_duplicated)

        expected_removed_admin_addr_list = [
            EthAddress("0x1000000000000000000000000000000000000000"),
            EthAddress("0x2000000000000000000000000000000000000000"),
            EthAddress("0x1000000000000000000000000000000000000000"),
            EthAddress("0x3000000000000000000000000000000000000000")
        ]
        result_removed_admin_addr = remove_admin_addresses_from(test_addr_list)
        self.assertNotEqual(test_addr_list, result_removed_admin_addr)
        self.assertEqual(expected_removed_admin_addr_list, result_removed_admin_addr)

        expected_removed_addr_list = [
            EthAddress("0x1000000000000000000000000000000000000000"),
            EthAddress("0x1000000000000000000000000000000000000000"),
            EthAddress("0x3000000000000000000000000000000000000000"),
            self.admin_addr
        ]

        to_removed_addr_list = [EthAddress("0x2000000000000000000000000000000000000000")]
        result_removed_addr = remove_addresses_from(test_addr_list, to_removed_addr_list)
        self.assertNotEqual(test_addr_list, result_removed_addr)
        self.assertEqual(expected_removed_addr_list, result_removed_addr)

        result_false = is_admin_relayer(self.user.active_account.address)
        self.assertFalse(result_false)
        result_true = is_admin_relayer(self.admin_addr)
        self.assertTrue(result_true)
