import enum
from typing import List

from chainpy.eth.ethtype.consts import Chain
from relayer.tools.utils import get_chain_from_console, display_receipt_status, get_option_from_console, Manager


class SupportedAdminCmd(enum.Enum):
    FETCH_ROUNDS = "fetch every round from each chain"
    ROUND_UP = "round up"
    BATCH_ROUND_UP = "batch round up"

    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedAdminCmd"]:
        return [cmd for cmd in SupportedAdminCmd]


def admin_cmd(project_root_path: str = "./"):
    admin = Manager.init_manager("admin", project_root_path)
    print(">>>  Admin Address: {}".format(admin.active_account.address.with_checksum()))

    while True:
        cmd = get_option_from_console("select a command number", SupportedAdminCmd.supported_cmds())
        if cmd == SupportedAdminCmd.FETCH_ROUNDS:
            print("-----------------------------------------------")
            for chain_index in admin.supported_chain_list:
                _round = admin.world_call(chain_index, "relayer_authority", "latest_round", [])[0]
                print("{:>8}: {}".format(chain_index.name, _round))
            print("-----------------------------------------------")

        elif cmd == SupportedAdminCmd.ROUND_UP:
            # round up
            chain_index = get_chain_from_console(admin)
            tx_hash = admin.round_up(chain_index)

            receipt = admin.world_receipt_with_wait(chain_index, tx_hash, False)
            display_receipt_status(receipt)

        elif cmd == SupportedAdminCmd.BATCH_ROUND_UP:
            # batch round up
            chain_index = get_chain_from_console(admin)
            bifnet_round = admin.world_call(Chain.BIFROST, "relayer_authority", "latest_round", [])[0]
            target_round = admin.world_call(chain_index, "relayer_authority", "latest_round", [])[0]
            if bifnet_round < target_round:
                raise Exception("target chain's round is bigger than bifrost network")

            print(">>> bifnet_round({}), {}_round({})".format(bifnet_round, chain_index.name, target_round))
            for _ in range(bifnet_round - target_round):
                tx_hash = admin.round_up(chain_index)
                receipt = admin.world_receipt_with_wait(chain_index, tx_hash, False)
                display_receipt_status(receipt)

            bifnet_round = admin.world_call(Chain.BIFROST, "relayer_authority", "latest_round", [])[0]
            target_round = admin.world_call(chain_index, "relayer_authority", "latest_round", [])[0]
            print(">>> bifnet_round({}), {}_round({})".format(bifnet_round, chain_index.name, target_round))

        else:
            return
