import enum
from typing import List

from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthAddress
from relayer.tools.consts import ADMIN_RELAYERS
from relayer.tools.utils import display_multichain_coins_balances, display_multichain_balances_on, \
    fetch_and_display_rounds, Manager, RelayerWithVersion, get_token_from_console
from relayer.tools.utils import get_option_from_console


class SupportedOperatorCmd(enum.Enum):
    PRINT_TEAM_AUTHORITIES = "print relayer preset"
    FETCH_EXTERNAL_AUTHORITY_LIST = "fetch authority list"
    FETCH_ROUNDS = "fetch every round from each chain"

    BALANCES_OF_AUTHORITIES = "balances of every authorities"
    BALANCES_OF_SOCKETS = "balances of every sockets"

    GET_PRICE_OF = "get price from oracle"
    GET_LATEST_BTC_HASH = "get latest BTC hash from oracle"
    # GET_BTC_HASH_OF_THE_HEIGHT = "get BTC hash of the height from oracle"

    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedOperatorCmd"]:
        return [cmd for cmd in SupportedOperatorCmd]


def operator_cmd(project_root_path: str = "./"):
    operator = Manager.init_manager("operator", project_root_path)
    print(">>>  Operator's Address: {}".format(operator.active_account.address.with_checksum()))

    while True:
        cmd = get_option_from_console("select a command number", SupportedOperatorCmd.supported_cmds())

        if cmd == SupportedOperatorCmd.PRINT_TEAM_AUTHORITIES:
            admin_relayers_with_version = [RelayerWithVersion(addr) for addr in ADMIN_RELAYERS]
            RelayerWithVersion.display_addrs(operator, "<admin relayers>", admin_relayers_with_version, False)

        elif cmd == SupportedOperatorCmd.FETCH_EXTERNAL_AUTHORITY_LIST:  # TODO version?
            # authority list
            validator_addr_list = operator.fetch_sorted_validator_list(ChainIndex.BIFROST)
            validator_addr_list = [RelayerWithVersion(addr) for addr in validator_addr_list]
            RelayerWithVersion.display_addrs(operator, "<fetched authority list>", validator_addr_list)

        elif cmd == SupportedOperatorCmd.FETCH_ROUNDS:
            fetch_and_display_rounds(operator)

        elif cmd == SupportedOperatorCmd.BALANCES_OF_AUTHORITIES:
            # validator coin balances
            validator_addr_list = operator.fetch_sorted_validator_list(ChainIndex.BIFROST)
            validator_addr_list = [EthAddress(addr) for addr in validator_addr_list]
            print("----------------------------------------------------------------------------------")
            for i, addr in enumerate(validator_addr_list):
                display_multichain_coins_balances(operator, addr)
            print("----------------------------------------------------------------------------------")

        elif cmd == SupportedOperatorCmd.BALANCES_OF_SOCKETS:
            # socket balance
            for chain_index in operator.supported_chain_list:
                vault_addr = operator.get_vault_addr(chain_index)  # spender
                display_multichain_balances_on(operator, chain_index, addr=vault_addr)

        elif cmd == SupportedOperatorCmd.GET_PRICE_OF:
            # get price from oracle
            token_stream_index = get_token_from_console()
            price = operator.fetch_price_from_oracle(token_stream_index)
            print(price.change_decimal(6).float_str)

        elif cmd == SupportedOperatorCmd.GET_LATEST_BTC_HASH:
            # get btc hash from oracle contract
            btc_hash = operator.fetch_btc_hash_from_oracle()
            print(btc_hash.hex())

        else:
            return
