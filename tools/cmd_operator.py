import enum
from typing import List

from bridgeconst.consts import Chain, Oracle
from chainpy.eth.ethtype.hexbytes import EthAddress

from rbclib.bifrostutils import (
    fetch_submitted_oracle_feed,
    fetch_btc_hash_from_oracle,
    fetch_price_from_oracle,
    fetch_oracle_latest_round,
    fetch_sorted_relayer_list_lower
)
from rbclib.switchable_enum import SwitchableChain

from .consts import TESTNET_TEAM_RELAYER, MAINNET_TEAM_RELAYER
from .utils import (
    display_multichain_coins_balances,
    display_multichain_balances_on,
    fetch_and_display_rounds,
    Manager,
    display_addrs,
    symbol_list_on,
    get_option_from_console
)


class SupportedOperatorCmd(enum.Enum):
    PRINT_TEAM_AUTHORITIES = "print relayer preset"
    FETCH_ROUNDS = "fetch every round from each chain"

    BALANCES_OF_AUTHORITIES = "balances of every authorities"  # TODO not tested
    BALANCES_OF_SOCKETS = "balances of every sockets"  # TODO not tested

    GET_LATEST_PRICE_OF = "get price from oracle"
    GET_LATEST_BTC_HASH = "get latest BTC hash from oracle"
    GET_BTC_HASH_OF_THE_HEIGHT = "get BTC hash of the height from oracle"
    GET_BTC_FEEDS_BY = "get btc hash feed of each relayer"
    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedOperatorCmd"]:
        return [cmd for cmd in SupportedOperatorCmd]


def operator_cmd(is_testnet: bool, ):
    operator = Manager.init_manager("User", is_testnet)
    print(">>>  Operator's Address: {}".format(operator.active_account.address.with_checksum()))

    while True:
        cmd = get_option_from_console("select a command number", SupportedOperatorCmd.supported_cmds())

        if cmd == SupportedOperatorCmd.PRINT_TEAM_AUTHORITIES:
            relayers = TESTNET_TEAM_RELAYER if is_testnet else MAINNET_TEAM_RELAYER
            display_addrs("Team Relayers", relayers)

        elif cmd == SupportedOperatorCmd.FETCH_ROUNDS:
            fetch_and_display_rounds(operator)

        elif cmd == SupportedOperatorCmd.BALANCES_OF_AUTHORITIES:
            # validator coin balances
            validator_addr_list = fetch_sorted_relayer_list_lower(operator, SwitchableChain.BIFROST)
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

        elif cmd == SupportedOperatorCmd.GET_LATEST_PRICE_OF:
            # get price from oracle
            symbols = symbol_list_on(SwitchableChain.BIFROST, is_testnet=is_testnet)
            symbol = get_option_from_console("Select Asset Symbol", symbols)
            price = fetch_price_from_oracle(operator, symbol)
            print(">>> Price: {}".format(price.change_decimal(6).float_str))

        elif cmd == SupportedOperatorCmd.GET_LATEST_BTC_HASH:
            # get btc hash from oracle contract
            btc_hash = fetch_btc_hash_from_oracle(operator)
            print("latest btc hash oracle answer: {}".format(btc_hash.hex()))

        elif cmd == SupportedOperatorCmd.GET_BTC_HASH_OF_THE_HEIGHT:
            print("TODO")

        elif cmd == SupportedOperatorCmd.GET_BTC_FEEDS_BY:
            relayers = fetch_sorted_relayer_list_lower(operator, SwitchableChain.BIFROST)
            latest_round = fetch_oracle_latest_round(operator, Oracle.BITCOIN_BLOCK_HASH)
            print("latest_round: {}".format(latest_round))
            for relayer in relayers:
                result = fetch_submitted_oracle_feed(
                    operator, Oracle.BITCOIN_BLOCK_HASH, latest_round, EthAddress(relayer)
                )
                print("addr: {} {}".format(relayer, result.hex()))

        else:
            return
