import enum
from typing import List

from chainpy.eth.ethtype.amount import EthAmount
from bridgeconst.consts import RBCMethodDirection, Asset, Symbol, RBCMethodV1
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHashBytes

from rbclib.switchable_enum import SwitchableChain
from relayer.user_utils import symbol_to_asset
from .utils import (
    get_typed_item_from_console,
    display_receipt_status,
    display_multichain_asset_balances,
    fetch_and_display_rounds,
    Manager,
    get_option_from_console,
    get_chain_and_symbol_from_console, cccp_batch_send, get_chain_from_console
)


class SupportedUserCmd(enum.Enum):
    FETCH_ROUNDS = "fetch every round from each chain"
    RBC_REQUEST = "rbc request"
    RBC_LOAD_TEST = "rbc batch request"
    RBC_ROLLBACK = "rbc reqeust rollback"

    TOKEN_APPROVE = "token approve"
    ASSET_TRANSFER = "transfer asset to target address"
    MY_BALANCES = "balance of myself"

    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedUserCmd"]:
        return [cmd for cmd in SupportedUserCmd]


def user_cmd(is_testnet: bool):
    user = Manager.init_manager("User", is_testnet)
    print(">>>  User Address: {}".format(user.active_account.address.with_checksum()))

    while True:
        cmd = get_option_from_console("select a command number", SupportedUserCmd.supported_cmds())

        if cmd == SupportedUserCmd.FETCH_ROUNDS:
            fetch_and_display_rounds(user)

        elif cmd == SupportedUserCmd.RBC_REQUEST or cmd == SupportedUserCmd.RBC_LOAD_TEST:
            # get a direction from console
            direction_str = get_option_from_console("select direction", ["INBOUND", "OUTBOUND"])
            direction = RBCMethodDirection[direction_str]

            # get a pair of chain and asset from console
            chain, symbol = get_chain_and_symbol_from_console(user, not_included_bifrost=True)

            # get a rbc-method (source chain and destination chain are determined)
            if direction == RBCMethodDirection.INBOUND:
                rbc_method = RBCMethodV1.WARP_UNIFY_SPLIT if symbol == Symbol.BFC else RBCMethodV1.WARP_UNIFY
                src_chain, dst_chain = chain, SwitchableChain.BIFROST,
            else:
                rbc_method = RBCMethodV1.UNIFY_SPLIT_WARP if symbol == Symbol.BFC else RBCMethodV1.SPLIT_WARP
                src_chain, dst_chain = SwitchableChain.BIFROST, chain

            # get an amount
            result = get_typed_item_from_console("Insert amount (int or float) to be sent to socket: ", float)
            amount = EthAmount(result, symbol.decimal)

            if cmd == SupportedUserCmd.RBC_REQUEST:
                print(">>> Send {} {} from {} to {} with {}".format(
                    amount.change_decimal(4).float_str,
                    symbol, src_chain,
                    dst_chain, rbc_method
                ))

                receipt, rid = user.send_cross_action_and_wait_receipt(src_chain, dst_chain, symbol, rbc_method, amount)
                display_receipt_status(receipt)
                print(">>> rid: ({}, {}, {})".format(rid[0].name, rid[1], rid[2]))
            else:
                req_num = get_typed_item_from_console("how many request? ", int)
                receipts, rids = cccp_batch_send(user, req_num, src_chain, dst_chain, symbol, rbc_method, amount)

                for i in range(req_num):
                    display_receipt_status(receipts[i])
                    rid = rids[i]
                    print(">>> rid: ({}, {}, {})".format(rid[0].name, rid[1], rid[2]))
            continue

        elif cmd == SupportedUserCmd.RBC_ROLLBACK:
            chain = get_chain_from_console(user)
            tx_hash = get_typed_item_from_console("Enter tx_hash to rollback", EthHashBytes)

            rollback_address, params = user.build_rollback_params(chain, tx_hash)
            print("rollback_address: {}".format(rollback_address.with_checksum()))

            rollback_asset = Asset.from_bytes(params[1][1][0])
            before_balance = user.world_balance(chain, rollback_asset, rollback_address)
            print("before balance: {} {}".format(
                before_balance.change_decimal(4).float_str, rollback_asset.symbol.name
            ))
            expected_balance = EthAmount(params[1][1][4], rollback_asset.decimal)
            print("expected balance: {} {}".format(
                expected_balance.change_decimal(4).float_str,
                rollback_asset.symbol.name
            ))

            tx = user.world_build_transaction(chain, "socket", "timeout_rollback", params)
            tx_hash = user.world_send_transaction(chain, tx)
            print(">>> Rollback {} {} to {}".format(
                (expected_balance - before_balance).change_decimal(4).float_str,
                rollback_asset.symbol, rollback_address.with_checksum()
            ))

            receipt = user.world_receipt_with_wait(chain, tx_hash)
            display_receipt_status(receipt)

            actual_balance = user.world_balance(chain, rollback_asset, rollback_address)
            print("actual balance: {} {}".format(
                actual_balance.change_decimal(4).float_str, rollback_asset.symbol.name
            ))

        elif cmd == SupportedUserCmd.TOKEN_APPROVE:
            # approve
            chain, symbol = get_chain_and_symbol_from_console(user, token_only=True)

            if symbol == Symbol.NONE:
                print("No token on the chain: {}".format(chain))
                continue

            vault_addr = user.get_vault_addr(chain)  # spender
            asset = symbol_to_asset(chain, symbol)
            tx_hash = user.token_approve(chain, asset, vault_addr, EthAmount(2 ** 255))
            print(">>> Approve {} on {}".format(
                asset.name, chain.name
            ))
            receipt = user.world_receipt_with_wait(chain, tx_hash, False)
            display_receipt_status(receipt)

        elif cmd == SupportedUserCmd.ASSET_TRANSFER:
            chain, symbol = get_chain_and_symbol_from_console(user, token_only=False)

            # insert address
            receiver_addr = get_typed_item_from_console("Enter an address to receive asset: ", EthAddress)

            # insert amount
            result = get_typed_item_from_console("Insert amount (int or float) to be sent to socket: ", float)
            amount = EthAmount(result, symbol.decimal)

            # build and send transaction
            asset = symbol_to_asset(chain, symbol)
            if asset.is_coin():
                tx_hash = user.world_transfer_coin(chain, receiver_addr, amount)
            else:
                tx = user.world_build_transaction(
                    chain,
                    asset.name,
                    "transfer",
                    [receiver_addr.with_checksum(), amount.int()]
                )
                tx_hash = user.world_send_transaction(chain, tx)

            print(">>> Transfer {} to {}".format(
                asset.name, receiver_addr.with_checksum()
            ))

            # check the receipt
            receipt = user.world_receipt_with_wait(chain, tx_hash, False)
            display_receipt_status(receipt)

        elif cmd == SupportedUserCmd.MY_BALANCES:
            # balanceOf
            display_multichain_asset_balances(user, user.active_account.address)

        else:
            # quit
            return
