import enum
from typing import List

from chainpy.eth.ethtype.account import EthAccount
from chainpy.eth.ethtype.amount import EthAmount
from bridgeconst.consts import Chain
from chainpy.eth.ethtype.hexbytes import EthAddress
from relayer.tools.consts import NOMINATION_AMOUNT
from relayer.tools.utils_recharger import fetch_healthy_relayers
from relayer.tools.utils import display_receipt_status, get_option_from_console, get_typed_item_from_console, \
    Manager


class SupportedNominatorCmd(enum.Enum):
    FETCH_HEALTHY_AUTHORITIES = "fetch healthy relayers"
    NOMINATE = "nominate to a specific "

    QUIT = "quit"

    @staticmethod
    def supported_cmds() -> List["SupportedNominatorCmd"]:
        return [cmd for cmd in SupportedNominatorCmd]


def nominator_cmd(project_root_path: str = "./"):
    nominator = Manager.init_manager("nominator", project_root_path)
    print(">>>  Nominator Address: {}".format(nominator.active_account.address.with_checksum()))

    while True:
        cmd = get_option_from_console("select a command number", SupportedNominatorCmd.supported_cmds())
        if cmd == SupportedNominatorCmd.FETCH_HEALTHY_AUTHORITIES:
            healthy_relayers = fetch_healthy_relayers(nominator, 80)
            healthy_relayers = [RelayerWithVersion(addr) for addr in healthy_relayers]

            nominations = list()
            for rwv in healthy_relayers:
                candidate_state = nominator.world_call(
                    Chain.BFC_TEST, "authority", "candidate_state", [rwv.relayer.hex()])
                nominations.append(candidate_state[0][5])

            RelayerWithVersion.display_addrs(nominator, "healthy_relayers", healthy_relayers)

        elif cmd == SupportedNominatorCmd.NOMINATE:
            validator_addr: EthAddress = get_typed_item_from_console(
                "enter a validator address to be nominated",
                EthAddress
            )

            dummy_account = EthAccount.generate()
            print("dummy_addr: {}".format(dummy_account.address.hex()))
            dummy_user = Manager.init_manager("User", project_root_path, dummy_account)

            _, tx_hash = nominator.world_transfer_coin(
                Chain.BFC_TEST,
                dummy_account.address,
                (NOMINATION_AMOUNT + EthAmount(1.0))
            )
            receipt = nominator.world_receipt_with_wait(Chain.BFC_TEST, tx_hash)
            print("transfer transaction")
            display_receipt_status(receipt)
            if receipt is None:
                raise Exception("receipt is None")
            if receipt.status != 1:
                raise Exception("transaction fails")

            tx = dummy_user.world_build_transaction(
                Chain.BFC_TEST,
                "authority",
                "nominate",
                [validator_addr.hex(), EthAmount(10000.0).int(), 100, 100]
            )
            _, tx_hash = dummy_user.world_send_transaction(Chain.BFC_TEST, tx)
            receipt = dummy_user.world_receipt_with_wait(Chain.BFC_TEST, tx_hash)
            print("nominate transaction")
            display_receipt_status(receipt)

        else:
            return
