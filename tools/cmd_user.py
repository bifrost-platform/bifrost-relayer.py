import enum
from typing import List

from chainpy.eth.ethtype.amount import EthAmount
from bridgeconst.consts import Chain, RBCMethodDirection, Asset, Symbol, RBCMethodV1
from chainpy.eth.ethtype.hexbytes import EthAddress

from rbclib.switchable_enum import SwitchableChain
from .consts import RBC_SUPPORTED_INBOUND_METHODS, RBC_SUPPORTED_OUTBOUND_METHODS
from .utils_load_test import cccp_batch_send
from .utils import (
    get_chain_and_asset_from_console_for_bridge,
    get_typed_item_from_console,
    display_receipt_status,
    display_multichain_asset_balances,
    fetch_and_display_rounds, Manager,
    get_chain_and_asset_from_console,
    get_option_from_console
)


class SupportedUserCmd(enum.Enum):
    FETCH_ROUNDS = "fetch every round from each chain"
    RBC_REQUEST = "rbc request"
    RBC_LOAD_TEST = "rbc batch request"
    # RBC_ROLLBACK = "rbc reqeust rollback"

    MY_BALANCE = "balance of myself"
    TOKEN_APPROVE = "token approve"
    ASSET_TRANSFER = "transfer asset to target address"

    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedUserCmd"]:
        return [cmd for cmd in SupportedUserCmd]


def user_cmd(is_testnet: bool, project_root_path: str = "./"):
    user = Manager.init_manager("User", is_testnet, project_root_path=project_root_path)
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
            chain, asset = get_chain_and_asset_from_console_for_bridge(user, direction, not_included_bifrost=True)

            # get a rbc-method (source chain and destination chain are determined)
            if direction == RBCMethodDirection.INBOUND:
                rbc_method = RBCMethodV1.WARP_UNIFY_SPLIT if asset.symbol == Symbol.BFC else RBCMethodV1.WARP_UNIFY
                src_chain, dst_chain = chain, SwitchableChain.BIFROST
            else:
                rbc_method = RBCMethodV1.UNIFY_SPLIT_WARP if asset.symbol == Symbol.BFC else RBCMethodV1.SPLIT_WARP
                src_chain, dst_chain = SwitchableChain.BIFROST, chain

            # get an amount
            result = get_typed_item_from_console("Insert amount (int or float) to be sent to socket: ", float)
            amount = EthAmount(result, asset.decimal)

            if SupportedUserCmd.RBC_REQUEST:
                print(">>> Send {} {} from {} to {} with {}".format(
                    amount.change_decimal(4).float_str,
                    asset, src_chain,
                    dst_chain, rbc_method
                ))

                receipt = user.send_cross_action_and_wait_receipt(src_chain, dst_chain, asset, rbc_method, amount)
                display_receipt_status(receipt)

                result = user.get_contract_obj_on(src_chain, "socket").\
                    get_method_abi("Socket").\
                    decode_event_data(receipt.logs[3].data)[0]
                print(">>> rid: ({}, {}, {})".format(Chain.from_bytes(result[0][0]), result[0][1], result[0][2]))

            else:
                req_num = get_typed_item_from_console("how many request? ", int)
                cccp_batch_send(user, req_num, dst_chain, src_chain, rbc_method)
            continue

        elif cmd == SupportedUserCmd.TOKEN_APPROVE:
            # approve
            chain, asset = get_chain_and_asset_from_console(user, True)

            if asset == Asset.NONE:
                print("No token on the chain: {}".format(chain))
                continue

            vault_addr = user.get_vault_addr(chain)  # spender
            tx_hash = user.token_approve(chain, asset, vault_addr, EthAmount(2 ** 255))
            receipt = user.world_receipt_with_wait(chain, tx_hash, False)
            display_receipt_status(receipt)

        elif cmd == SupportedUserCmd.MY_BALANCE:
            # balanceOf
            display_multichain_asset_balances(user, user.active_account.address)

        elif cmd == SupportedUserCmd.ASSET_TRANSFER:
            chain, asset = get_chain_and_asset_from_console(user)

            # insert address
            addr_str = input("enter an address to receive asset: ")
            addr = EthAddress(addr_str)

            # insert amount
            amount = get_typed_item_from_console(">>> Insert amount (in float) to be sent: ", float)
            amount = EthAmount(amount, asset.decimal) if amount is not None else EthAmount(0.1, asset.decimal)

            # build and send transaction
            if asset.is_coin_on(chain):
                _, tx_hash = user.world_transfer_coin(chain, addr, amount)
            else:
                tx = user.world_build_transaction(
                    chain,
                    asset.name,
                    "transfer",
                    [addr.with_checksum(), amount.int()]
                )
                _, tx_hash = user.world_send_transaction(chain, tx)

            # check the receipt
            receipt = user.world_receipt_with_wait(chain, tx_hash, False)
            display_receipt_status(receipt)

        else:
            # quit
            return
