import enum
import json
from typing import List

from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthAddress
from relayer.tools.consts import ADMIN_RELAYERS
from relayer.tools.utils import get_chain_index_from_console, display_receipt_status, get_option_from_console, \
    init_manager


class SupportedAdminCmd(enum.Enum):
    FETCH_AUTHORITY_LIST = "fetch authority list"
    ROUND_UP = "round up"
    FETCH_ROUNDS = "fetch every round from each chain"
    BATCH_ROUND_UP = "batch round up"

    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedAdminCmd"]:
        return [cmd for cmd in SupportedAdminCmd]


def admin_cmd(project_root_path: str = "./"):
    admin = init_manager("admin", project_root_path)
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
            chain_index = get_chain_index_from_console(admin)
            validator_addr_list = admin.world_call(ChainIndex.BIFROST, "relayer_authority", "selected_relayers", [True])[0]
            print(">>> current_validators \n{}".format(json.dumps(validator_addr_list, indent=4)))

            relayer_preset = [*ADMIN_RELAYERS, "No change"]
            validator_addr_to_change = get_option_from_console("select a validator to ignore", relayer_preset)

            if validator_addr_to_change != "No change":
                validator_addr_to_change = EthAddress(validator_addr_to_change)
            else:
                validator_addr_to_change = None
            tx_hash = admin.round_up(chain_index, validator_addr_to_change)

            receipt = admin.world_receipt_with_wait(chain_index, tx_hash, False)
            display_receipt_status(receipt)

        elif cmd == SupportedAdminCmd.BATCH_ROUND_UP:
            # batch round up
            chain_index = get_chain_index_from_console(admin)
            bifnet_round = admin.world_call(ChainIndex.BIFROST, "relayer_authority", "latest_round", [])[0]
            target_round = admin.world_call(chain_index, "relayer_authority", "latest_round", [])[0]
            print(">>> bifnet_round({}), {}_round({})".format(bifnet_round, chain_index.name, target_round))

            for i in range(bifnet_round - target_round):
                tx_hash = admin.round_up(chain_index)
                receipt = admin.world_receipt_with_wait(chain_index, tx_hash, False)
                display_receipt_status(receipt)
                target_round = admin.world_call(chain_index, "relayer_authority", "latest_round", [])[0]
                print(">>> bifnet_round({}), {}_round({})".format(bifnet_round, chain_index.name, target_round))

        else:
            return
