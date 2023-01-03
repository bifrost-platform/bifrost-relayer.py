import enum
from typing import List

from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.consts import Chain
from chainpy.eth.ethtype.hexbytes import EthAddress
from rbclib.consts import Bridge
from relayer.tools.consts import RBC_SUPPORTED_METHODS
from relayer.tools.utils_load_test import cccp_batch_send
from relayer.tools.utils import get_chain_and_token_from_console, determine_decimal, get_typed_item_from_console, \
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

        elif cmd == SupportedUserCmd.RBC_REQUEST:
            # cross chain action
            direction_str = get_option_from_console("select direction", ["inbound", "outbound"])
            chain_index, token_index = get_chain_and_token_from_console(user, not_included_bifrost=True)

            # insert cross-method
            method_index = get_option_from_console("method", RBC_SUPPORTED_METHODS)

            # set amount as default
            decimal = determine_decimal(token_index)
            if direction_str == "inbound":
                src_chain_index, dst_chain_index, amount = chain_index, Chain.BIFROST, EthAmount(0.02, decimal)
            elif direction_str == "outbound":
                src_chain_index, dst_chain_index, amount = Chain.BIFROST, chain_index, EthAmount(0.01, decimal)
            else:
                raise Exception("Not supported direction")

            # insert amount
            amount_float = get_typed_item_from_console(">>> Insert amount (in float) to be sent to socket: ", float)
            amount = EthAmount(amount_float, decimal) if amount_float is not None else amount

            # build and send transaction
            receipt = user.send_cross_action_and_wait_receipt(
                src_chain_index, dst_chain_index, token_index, method_index, amount)

            # check receipt
            display_receipt_status(receipt)
            continue

        elif cmd == SupportedUserCmd.RBC_LOAD_TEST:
            req_num = get_typed_item_from_console("how many request? ", int)
            direction = get_option_from_console("select a direction: inbound or outbound", ["inbound", "outbound"])
            cccp_batch_send(user, {"txNum": req_num, "direction": direction})

        elif cmd == SupportedUserCmd.TOKEN_APPROVE:
            # approve
            chain_index, token_index = get_chain_and_token_from_console(user, True)
            if token_index == Bridge.NONE:
                print(">>> There is no option.")
                continue

            vault_addr = user.get_vault_addr(chain_index)  # spender
            _, tx_hash = user.token_approve(chain_index, token_index, vault_addr, EthAmount(2 ** 255))
            receipt = user.world_receipt_with_wait(chain_index, tx_hash, False)
            display_receipt_status(receipt)

        # elif cmd == SupportedUserCmd.RBC_ROLLBACK:
        #     raise Exception("Not implementation yet")

        elif cmd == SupportedUserCmd.MY_BALANCE:
            # balanceOf
            display_multichain_asset_balances(user, user.active_account.address)

        elif cmd == SupportedUserCmd.ASSET_TRANSFER:
            chain_index, token_index = get_chain_and_token_from_console(user)
            decimal = determine_decimal(token_index)

            # insert address
            addr_str = input("enter an address to receive asset: ")
            addr = EthAddress(addr_str)

            # insert amount
            amount_float = get_typed_item_from_console(">>> Insert amount (in float) to be sent: ", float)
            amount = EthAmount(amount_float, decimal) if amount_float is not None else EthAmount(0.1, decimal)

            # build and send transaction
            if token_index.is_coin_on(chain_index):
                _, tx_hash = user.world_transfer_coin(chain_index, addr, amount)
            else:
                tx = user.world_build_transaction(
                    chain_index,
                    token_index.name,
                    "transfer",
                    [addr.with_checksum(), amount.int()]
                )
                _, tx_hash = user.world_send_transaction(chain_index, tx)

            # check the receipt
            receipt = user.world_receipt_with_wait(chain_index, tx_hash, False)
            display_receipt_status(receipt)

        else:
            # quit
            return
