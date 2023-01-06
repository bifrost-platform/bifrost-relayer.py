import enum
from typing import List

from chainpy.eth.ethtype.amount import EthAmount
from bridgeconst.consts import Chain, RBCMethodDirection, Asset
from chainpy.eth.ethtype.hexbytes import EthAddress

from relayer.tools.consts import RBC_SUPPORTED_INBOUND_METHODS, RBC_SUPPORTED_OUTBOUND_METHODS
from relayer.tools.utils_load_test import cccp_batch_send
from relayer.tools.utils import get_chain_and_asset_from_console, get_typed_item_from_console, \
    display_receipt_status, display_multichain_asset_balances, fetch_and_display_rounds, Manager
from relayer.tools.utils import get_option_from_console


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


def user_cmd(project_root_path: str = "./"):
    user = Manager.init_manager("User", project_root_path)
    print(">>>  User Address: {}".format(user.active_account.address.with_checksum()))

    while True:
        cmd = get_option_from_console("select a command number", SupportedUserCmd.supported_cmds())

        if cmd == SupportedUserCmd.FETCH_ROUNDS:
            fetch_and_display_rounds(user)

        elif cmd == SupportedUserCmd.RBC_REQUEST or cmd == SupportedUserCmd.RBC_LOAD_TEST:
            # cross chain action
            result = get_option_from_console("select direction", ["inbound", "outbound"])
            dir_obj = RBCMethodDirection[result.upper()]
            chain, asset = get_chain_and_asset_from_console(user, dir_obj, not_included_bifrost=True)

            # insert cross-method
            if dir_obj == RBCMethodDirection.INBOUND:
                rbc_method = get_option_from_console("method", RBC_SUPPORTED_INBOUND_METHODS)
                src_chain, dst_chain, amount = chain, Chain.BFC_TEST, EthAmount(0.02, asset.decimal)
            else:
                rbc_method = get_option_from_console("method", RBC_SUPPORTED_OUTBOUND_METHODS)
                src_chain, dst_chain, amount = Chain.BFC_TEST, chain, EthAmount(0.01, asset.decimal)

            print(src_chain.name)
            print(dst_chain.name)

            # insert amount
            result = get_typed_item_from_console(">>> Insert amount (in float) to be sent to socket: ", float)
            amount = EthAmount(result, asset.decimal) if result is not None else amount

            if SupportedUserCmd.RBC_REQUEST:
                receipt = user.send_cross_action_and_wait_receipt(src_chain, dst_chain, asset, rbc_method, amount)
                display_receipt_status(receipt)
            else:
                req_num = get_typed_item_from_console("how many request? ", int)
                cccp_batch_send(user, req_num, dst_chain, src_chain, rbc_method)
            continue

        elif cmd == SupportedUserCmd.TOKEN_APPROVE:
            # approve
            chain, asset = get_chain_and_asset_from_console(user, True)

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
