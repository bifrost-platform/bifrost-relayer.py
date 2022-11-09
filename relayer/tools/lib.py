from typing import Union

from relayer.chainpy.eth.ethtype.amount import EthAmount
from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.relayer import Relayer
from relayer.user import User


def fetch_and_display_rounds(manager: Union[User, Relayer]):
    print("-----------------------------------------------")
    for chain_index in manager.supported_chain_list:
        _round = manager.world_call(chain_index, "relayer_authority", "latest_round", [])[0]
        print("{:>8}: {}".format(chain_index.name, _round))
    print("-----------------------------------------------")
