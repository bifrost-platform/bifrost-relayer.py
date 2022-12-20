import copy
import json

from typing import Union, List, Any, Optional
import requests
from chainpy.eth.ethtype.account import EthAccount
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.chaindata import EthReceipt
from chainpy.eth.ethtype.consts import ChainIndex
from chainpy.eth.ethtype.hexbytes import EthAddress
from chainpy.eth.managers.multichainmanager import MultiChainManager
from rbclib.consts import BridgeIndex
from relayer.relayer import Relayer
from relayer.tools.consts import ADMIN_RELAYERS, USER_CONFIG_PATH, PRIVATE_CONFIG_PATH, SUPPORTED_TOKEN_LIST, \
    CONTROLLER_TO_DISCORD_ID, SCORE_SERVER_URL, KNOWN_RELAYER
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


class RelayerWithVersion:
    def __init__(self, addr: Union[EthAddress, str], version: int = None):
        self.relayer = addr if isinstance(addr, EthAddress) else EthAddress(addr)
        self.controller = None
        self.discord = None
        self.version = version

    def __eq__(self, other):
        if isinstance(other, RelayerWithVersion):
            return self.relayer == other.relayer
        elif isinstance(other, str):
            return self.relayer.hex().lower() == other.lower()
        elif isinstance(other, EthAddress):
            return self.relayer == other
        else:
            raise Exception("other must be RelayerInfo or str or EthAddress, but {}".format(type(other)))

    @classmethod
    def from_resp(cls, result: dict):
        return RelayerWithVersion(EthAddress(result["_id"]), int(result["version"][-1]))

    @staticmethod
    def fetch_relayers_once_with_version() -> List["RelayerWithVersion"]:
        """ Fetch relayer addresses from the score server. and return addresses w/ duplicated"""
        response_json = requests.get(SCORE_SERVER_URL).json()

        ret = list()
        for result in response_json["relayers"]:
            if result["_id"] == "0x0":
                continue

            if result["_id"].lower() not in KNOWN_RELAYER:
                continue

            ret.append(RelayerWithVersion.from_resp(result))

        return ret

    @staticmethod
    def remove_duplicated(rifs: List["RelayerWithVersion"]):
        ret = list()
        rif_clone = copy.deepcopy(rifs)
        for rif in rif_clone:
            if rif not in rifs:
                ret.append(rif)
        return ret

    @staticmethod
    def difference(
            rifs: List["RelayerWithVersion"],
            comparison: Union[List["RelayerWithVersion"], List[EthAddress]]
    ) -> List["RelayerWithVersion"]:
        ret = list()
        for rif in rifs:
            if rif not in comparison:
                ret.append(rif)
        return ret

    @staticmethod
    def remove_team_authority(rifs: List["RelayerWithVersion"]) -> List["RelayerWithVersion"]:
        return RelayerWithVersion.difference(rifs, ADMIN_RELAYERS)

    @staticmethod
    def display_addrs(
            manager: Manager, title: str, addrs: List["RelayerWithVersion"], not_admin: bool = True):

        if len(addrs) == 0:
            return

        print(title)
        print("-----------------------------------------------------" * 2)
        j = 0
        for i, addr in enumerate(addrs):
            if not_admin and addr.is_team_relayer():
                continue
            if not addr.is_registered_relayer(manager):
                continue

            msg = "{:>2}: r({}) c({}) v({}) d({})".format(
                j, addr.relayer.with_checksum(),
                addr.get_controller_of(manager).with_checksum(),
                addr.version if addr.version is not None else 0,
                addr.get_discord_id(manager)
            )
            j += 1
            print(msg)
        print("-----------------------------------------------------" * 2)

    def is_team_relayer(self):
        return self.relayer.with_checksum() in ADMIN_RELAYERS

    def get_controller_of(self, manager: Manager) -> EthAddress:
        if self.controller is None:
            result = manager.world_call(ChainIndex.BIFROST, "relayer_authority", "relayer_pool", [])

            relayers, controllers = result[0], result[1]
            target_relayer = self.relayer.hex().lower()
            if target_relayer in relayers:
                idx = relayers.index(target_relayer)
                self.controller = EthAddress(controllers[idx])
            else:
                self.controller = EthAddress.zero()
        return self.controller

    def get_discord_id(self, manager: Manager) -> Optional[str]:
        if self.discord is None:
            controller = self.get_controller_of(manager).with_checksum()
            if controller in CONTROLLER_TO_DISCORD_ID.keys():
                self.discord = CONTROLLER_TO_DISCORD_ID[controller]
            else:
                self.discord = None
        return self.discord

    def is_registered_relayer(self, manager: Manager) -> bool:
        controller = self.get_controller_of(manager)
        return controller != EthAddress.zero()


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
        manager: Manager, chain_index: ChainIndex,
        addr: EthAddress = None, no_print_title: bool = False, coin_only: bool = False):
    target_addr = manager.active_account.address if addr is None else addr
    if not no_print_title:
        print("\n<{} balances on {}>".format(target_addr.hex(), chain_index))

    print(chain_index.name + "-" * (BALANCE_FORMAT_STRING_LEN * INLINE_BALANCES_NUM + 1 - len(chain_index.name)))
    bal_str, bal_num = "", 0
    target_asset_list = asset_list_of(chain_index)
    for token in target_asset_list:
        if token.is_coin_on(chain_index):
            bal = manager.world_native_balance(chain_index, target_addr)
        else:
            if coin_only:
                continue
            bal = manager.world_token_balance_of(chain_index, token, target_addr)
        balance_str = "> 1M" if bal > EthAmount(1000000.0) else bal.change_decimal(2).float_str
        bal_str += BALANCE_FORMAT.format(token.token_name(), balance_str)
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


def get_chain_from_console(manager: MultiChainManager, not_included_bifrost: bool = False) -> ChainIndex:
    # remove BIFROST from the supported chain list
    supported_chain_list_clone = copy.deepcopy(manager.supported_chain_list)
    if not_included_bifrost:
        supported_chain_list_clone.remove(ChainIndex.BIFROST)

    prompt = "select a chain"
    chain_index = get_option_from_console(prompt, supported_chain_list_clone)
    return chain_index


# not tested
def get_token_from_console(chain_index: ChainIndex = None, token_only: bool = False) -> BridgeIndex:
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
        return BridgeIndex.NONE
    else:
        return get_option_from_console(prompt, options)


def get_chain_and_token_from_console(
        manager: MultiChainManager,
        token_only: bool = False,
        not_included_bifrost: bool = False) -> (ChainIndex, BridgeIndex):
    chain_index = get_chain_from_console(manager, not_included_bifrost)
    token_index = get_token_from_console(chain_index, token_only)
    return chain_index, token_index


def asset_list_of(chain_index: ChainIndex = None):
    ret = []
    if chain_index is None or chain_index == ChainIndex.BIFROST:
        return SUPPORTED_TOKEN_LIST

    for token_stream_index in SUPPORTED_TOKEN_LIST:
        if token_stream_index.home_chain_index() == chain_index:
            ret.append(token_stream_index)
        if chain_index == ChainIndex.ETHEREUM and token_stream_index == BridgeIndex.BFC_BIFROST:
            ret.append(token_stream_index)
    return ret


def determine_decimal(token_index: BridgeIndex) -> int:
    return 6 if token_index == BridgeIndex.USDT_ETHEREUM or token_index == BridgeIndex.USDC_ETHEREUM else 18


def fetch_and_display_rounds(manager: Union[User, Relayer]):
    print("-----------------------------------------------")
    for chain_index in manager.supported_chain_list:
        _round = manager.world_call(chain_index, "relayer_authority", "latest_round", [])[0]
        print("{:>8}: {}".format(chain_index.name, _round))
    print("-----------------------------------------------")
