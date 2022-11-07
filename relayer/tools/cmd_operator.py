import enum
from typing import List

from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthAddress
from relayer.relayer import Relayer
from relayer.tools.consts import ADMIN_RELAYERS
from relayer.tools.utils import display_addrs, display_coins_balances, init_manager, get_token_index_from_console
from relayer.tools.utils import get_option_from_console


class SupportedOperatorCmd(enum.Enum):
    PRINT_RELAYER_PRESET = "print relayer preset"
    FETCH_ROUNDS = "fetch every round from each chain"
    FETCH_AUTHORITY_LIST = "fetch authority list"
    BALANCES_OF_AUTHORITIES = "balances of every authorities"
    # BALANCES_OF_SOCKETS = "balances of every sockets"

    # GET_PRICE_OF = "get price from oracle"
    # GET_LATEST_BTC_HASH = "get latest BTC hash from oracle"
    # GET_BTC_HASH_OF_THE_HEIGHT = "get BTC hash of the height from oracle"

    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedOperatorCmd"]:
        return [cmd for cmd in SupportedOperatorCmd]


def operator_cmd(project_root_path: str = "./"):
    operator: Relayer = init_manager("operator", project_root_path)
    print(">>>  User Address: {}".format(operator.active_account.address.with_checksum()))

    while True:
        cmd = get_option_from_console("select a command number", SupportedOperatorCmd.supported_cmds())

        if cmd == SupportedOperatorCmd.PRINT_RELAYER_PRESET:
            display_addrs("<admin relayers>", ADMIN_RELAYERS)

        elif cmd == SupportedOperatorCmd.FETCH_ROUNDS:
            print("-----------------------------------------------")
            for chain_index in operator.supported_chain_list:
                _round = operator.fetch_validator_round(chain_index)
                print("{:>8}: {}".format(chain_index.name, _round))
            print("-----------------------------------------------")

        elif cmd == SupportedOperatorCmd.FETCH_AUTHORITY_LIST:
            # authority list
            validator_addr_list = operator.fetch_sorted_validator_list(ChainIndex.BIFROST)
            validator_addr_list = [EthAddress(addr) for addr in validator_addr_list]
            display_addrs(operator, "<fetched authority list>", validator_addr_list)

        elif cmd == SupportedOperatorCmd.BALANCES_OF_AUTHORITIES:
            # validator coin balances
            validator_addr_list = operator.fetch_sorted_validator_list(ChainIndex.BIFROST)
            validator_addr_list = [EthAddress(addr) for addr in validator_addr_list]
            print("----------------------------------------------------------------------------------")
            for i, addr in enumerate(validator_addr_list):
                display_coins_balances(operator, addr)
            print("----------------------------------------------------------------------------------")

        # elif cmd == SupportedOperatorCmd.BALANCES_OF_SOCKETS:
        #     # socket balance
        #     for chain_index in operator.supported_chain_list:
        #         vault_addr = operator.get_vault_addr(chain_index)  # spender
        #         display_asset_balances_on_chain(operator, chain_index, addr=vault_addr)
        #
        # elif cmd == SupportedOperatorCmd.GET_PRICE_OF:
        #     # get price from oracle
        #     token_stream_index = get_token_index_from_console()
        #     price = operator.fetch_price_from_oracle(token_stream_index)
        #     print(price.change_decimal(6).float_str)
        #
        # elif cmd == SupportedOperatorCmd.GET_LATEST_BTC_HASH:
        #     # get btc hash from oracle contract
        #     btc_hash = operator.fetch_btc_block_hash()
        #     print(btc_hash.hex())q

        else:
            return
