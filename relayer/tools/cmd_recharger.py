from time import sleep

from relayer.chainpy.eth.ethtype.hexbytes import EthAddress
from relayer.tools.consts import ADMIN_RELAYERS
from relayer.tools.relayer_healty import fetch_once_relayers, fetch_healthy_relayers, ScoreClient, get_controller_of, \
    get_discord_id_by_controller
from relayer.tools.utils import display_coins_balances, remove_admin_addresses_from, \
    remove_addresses_from, display_addrs, init_manager


def recharger_forever(project_root_path: str = "./"):

    recharger = init_manager("recharger", project_root_path)
    while True:
        display_coins_balances(recharger)

        # relayers who have been turned on at least once.
        once_relayers = fetch_once_relayers()
        once_relayer_not_our = remove_admin_addresses_from(once_relayers)

        # healthy relayers
        healthy_relayers = fetch_healthy_relayers(recharger, 120)
        healthy_relayers_not_our = remove_admin_addresses_from(healthy_relayers)
        not_healthy_relayers_our = remove_addresses_from([EthAddress(addr) for addr in ADMIN_RELAYERS], healthy_relayers)
        display_addrs("not healthy our relayers", not_healthy_relayers_our)

        healthy_relayers_controllers = [get_controller_of(recharger, addr) for addr in healthy_relayers_not_our]
        display_addrs(
            "healthy relayers",
            healthy_relayers_not_our,
            auxiliary_addrs=healthy_relayers_controllers,
            auxiliary_strs=[get_discord_id_by_controller(addr) for addr in healthy_relayers_controllers]
        )

        # troll relayers
        troll_relayers = remove_addresses_from(once_relayer_not_our, healthy_relayers)
        troll_relayers_controllers = [get_controller_of(recharger, addr) for addr in troll_relayers]
        display_addrs(
            "troll relayers",
            troll_relayers,
            auxiliary_addrs=troll_relayers_controllers,
            auxiliary_strs=[get_discord_id_by_controller(addr) for addr in troll_relayers_controllers]

        )

        # recharge coins to once_relayers
        print("\n >>> start recharge")
        ScoreClient.recharge_coins(recharger, once_relayers)
        print("\n >>> end recharge. go to sleep for 2 minutes")
        sleep(30)
