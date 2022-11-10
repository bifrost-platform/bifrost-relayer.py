from time import sleep

from relayer.tools.utils_recharger import fetch_healthy_relayers, recharge_coins
from relayer.tools.utils import display_multichain_coins_balances, RelayerWithVersion, Manager


def relayer_manager(project_root_path: str = "./", recharge: bool = False):

    recharger = Manager.init_manager("recharger", project_root_path)
    while True:
        display_multichain_coins_balances(recharger)

        # relayers who have been turned on at least once.
        once_relayers_info = RelayerWithVersion.fetch_relayers_once_with_version()  # info
        once_relayer_addrs = [addr.relayer for addr in once_relayers_info]

        # healthy relayers
        healthy_relayers = fetch_healthy_relayers(recharger, 120)  # address
        healthy_relayers_info = list()
        for addr in healthy_relayers:
            if addr in once_relayer_addrs:
                idx = once_relayer_addrs.index(addr)
                healthy_relayers_info.append(RelayerWithVersion(addr, once_relayers_info[idx].version))
            else:
                healthy_relayers_info.append(RelayerWithVersion(addr, 7))

        RelayerWithVersion.display_addrs(recharger, "healthy relayers", healthy_relayers_info)

        not_healthy_relayers_info = RelayerWithVersion.difference(once_relayers_info, healthy_relayers_info)
        RelayerWithVersion.display_addrs(recharger, "not healthy relayers", not_healthy_relayers_info)

        if recharge:
            # recharge coins to once_relayers
            print("\n >>> start recharge")
            recharge_coins(recharger, once_relayer_addrs)
            print("\n >>> end recharge.")
        print("\n >>> sleep for 30 seconds.")
        sleep(30)
