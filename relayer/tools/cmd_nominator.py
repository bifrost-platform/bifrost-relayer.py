import enum
from typing import List

from relayer.chainpy.eth.ethtype.account import EthAccount
from relayer.chainpy.eth.ethtype.amount import EthAmount
from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthAddress
from relayer.tools.consts import NOMINATION_AMOUNT
from relayer.tools.relayer_healty import fetch_healthy_relayers
from relayer.tools.utils import display_receipt_status, \
    get_option_from_console, get_typed_item_from_console, display_addrs, init_manager, get_controller_of


class SupportedNominatorCmd(enum.Enum):
    FETCH_HEALTHY_AUTHORITIES = "fetch healthy relayers"
    NOMINATE = "nominate to a specific "

    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedNominatorCmd"]:
        return [cmd for cmd in SupportedNominatorCmd]


def nominator_cmd(project_root_path: str = "./"):
    nominator = init_manager("nominator", project_root_path)
    print(">>>  Nominator Address: {}".format(nominator.active_account.address.with_checksum()))

    while True:
        cmd = get_option_from_console("select a command number", SupportedNominatorCmd.supported_cmds())
        if cmd == SupportedNominatorCmd.FETCH_HEALTHY_AUTHORITIES:
            healthy_relayers = fetch_healthy_relayers(nominator, 80)
            nominations = list()
            for addr in healthy_relayers:
                candidate_state = nominator.world_call(ChainIndex.BIFROST, "authority", "candidate_state", [addr.hex()])
                nominations.append(candidate_state[0][5])

            display_addrs(nominator, "healthy_relayers", healthy_relayers)

        elif cmd == SupportedNominatorCmd.NOMINATE:
            validator_addr: EthAddress = get_typed_item_from_console(
                "enter a validator address to be nominated",
                EthAddress
            )

            dummy_account = EthAccount.generate()
            print("dummy_addr: {}".format(dummy_account.address.hex()))
            dummy_user = init_manager("User", project_root_path, dummy_account)

            _, tx_hash = nominator.world_transfer_coin(
                ChainIndex.BIFROST,
                dummy_account.address,
                (NOMINATION_AMOUNT + EthAmount(1.0))
            )
            receipt = nominator.world_receipt_with_wait(ChainIndex.BIFROST, tx_hash)
            print("transfer transaction")
            display_receipt_status(receipt)
            if receipt is None:
                raise Exception("receipt is None")
            if receipt.status != 1:
                raise Exception("transaction fails")

            tx = dummy_user.world_build_transaction(
                ChainIndex.BIFROST,
                "authority",
                "nominate",
                [validator_addr.hex(), EthAmount(10000.0).int(), 100, 100]
            )
            _, tx_hash = dummy_user.world_send_transaction(ChainIndex.BIFROST, tx)
            receipt = dummy_user.world_receipt_with_wait(ChainIndex.BIFROST, tx_hash)
            print("nominate transaction")
            display_receipt_status(receipt)

        else:
            return
