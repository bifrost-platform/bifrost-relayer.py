from typing import Dict

from chainpy.eth.ethtype.consts import ChainIndex
from chainpy.eth.ethtype.hexbytes import EthAddress
from prometheus_client import start_http_server, Summary, Counter, Gauge

from rbclib.consts import ChainEventStatus

SUPPORTED_CHAINS = [ChainIndex.BIFROST, ChainIndex.ETHEREUM, ChainIndex.BINANCE, ChainIndex.POLYGON]


REQUEST_COUNTERS: Dict[ChainEventStatus, Dict[ChainIndex, Counter]] = dict()
INCOMPLETE_SCORE_GAUGE: Dict[ChainIndex, Gauge] = dict()
for chain_index in SUPPORTED_CHAINS:
    """ add 3 when a REQUESTED is discovered. subtract 1 when the others are discovered. """
    INCOMPLETE_SCORE_GAUGE[chain_index] = Gauge(
        "incomplete_gauge_of_{}".format(chain_index.name),
        "Description of counter"
    )

    for status in ChainEventStatus:
        if status == ChainEventStatus.NONE:
            continue
        if REQUEST_COUNTERS.get(status) is None:
            REQUEST_COUNTERS[status] = dict()
        REQUEST_COUNTERS[status][chain_index] = Counter(
            '{}_counter_starts_on_{}'.format(status.name, chain_index.name),
            'Description of counter'
        )


def exporting_request_metric(_chain_index: ChainIndex, _status: ChainEventStatus, relayer_addr: EthAddress):
    if relayer_addr == "0x9342CeaAc2d83a35e3d2fFEE4aADe9c3e87e00B7":
        REQUEST_COUNTERS[_status][_chain_index].inc()

        if _status == ChainEventStatus.ACCEPTED or _status == ChainEventStatus.REJECTED:
            # do nothing
            pass
        elif _status == ChainEventStatus.REQUESTED:
            INCOMPLETE_SCORE_GAUGE[_chain_index].inc(2)
        else:
            INCOMPLETE_SCORE_GAUGE[_chain_index].dec(1)
