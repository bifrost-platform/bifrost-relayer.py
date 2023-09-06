import enum
from typing import List

from bridgeconst.consts import Chain, Oracle
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHashBytes

from rbclib.bifrostutils import (
    fetch_submitted_oracle_feed,
    fetch_btc_hash_from_oracle,
    fetch_price_from_oracle,
    fetch_oracle_latest_round,
    fetch_sorted_relayer_list_lower
)
from rbclib.switchable_enum import chain_primitives
from .consts import TESTNET_TEAM_RELAYER, MAINNET_TEAM_RELAYER
from .utils import (
    display_multichain_coins_balances,
    display_multichain_balances_on,
    fetch_and_display_rounds,
    Manager,
    display_addrs,
    symbol_list_on,
    get_option_from_console, get_typed_item_from_console, get_chain_from_console
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
    FETCH_AND_DECODE_EVENT = "decode socket event"
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
            validator_addr_list = fetch_sorted_relayer_list_lower(operator, chain_primitives.BIFROST)
            validator_addr_list = [EthAddress(addr) for addr in validator_addr_list]
            print("----------------------------------------------------------------------------------")
            for i, addr in enumerate(validator_addr_list):
                display_multichain_coins_balances(operator, addr)
            print("----------------------------------------------------------------------------------")

        elif cmd == SupportedOperatorCmd.BALANCES_OF_SOCKETS:
            # socket balance
            for chain_name in operator.supported_chain_list:
                chain = Chain[chain_name]
                vault_addr = operator.get_vault_addr(chain)  # spender
                display_multichain_balances_on(operator, chain, addr=vault_addr)

        elif cmd == SupportedOperatorCmd.GET_LATEST_PRICE_OF:
            # get price from oracle
            symbols = symbol_list_on(chain_primitives.BIFROST, is_testnet=is_testnet)
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
            relayers = fetch_sorted_relayer_list_lower(operator, chain_primitives.BIFROST)
            latest_round = fetch_oracle_latest_round(operator, Oracle.BITCOIN_BLOCK_HASH)
            print("latest_round: {}".format(latest_round))
            for relayer in relayers:
                result = fetch_submitted_oracle_feed(
                    operator, Oracle.BITCOIN_BLOCK_HASH, latest_round, EthAddress(relayer)
                )
                print("addr: {} {}".format(relayer, result.hex()))

        elif cmd == SupportedOperatorCmd.FETCH_AND_DECODE_EVENT:
            input_type = get_option_from_console("select input type", ["tx_hash", "log_data"])
            if input_type == "tx_hash":
                tx_hash = get_typed_item_from_console("enter tx_hash", EthHashBytes)
                chain = get_chain_from_console(operator)

                receipt = operator.world_receipt_without_wait(chain.name, tx_hash)
                if receipt is None:
                    print("No receipt")
                    return
                if receipt.status == 0:
                    print("failed transaction")
                    return
                log_data = receipt.get_log_data_by_topic("0x918454f530580823dd0d8cf59cacb45a6eb7cc62f222d7129efba5821e77f191")

            elif input_type == "log_data":
                log_data = get_typed_item_from_console("enter log_data", EthHashBytes)
                chain = chain_primitives.BIFROST
            else:
                raise Exception("Invalid input type")

            result = operator.get_contract_obj_on(chain.name, "socket").get_method_abi("Socket").decode_event_data(
                log_data)
            print(result)
            return

        else:
            return
