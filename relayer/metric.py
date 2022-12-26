from typing import Dict, List

from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.consts import ChainIndex
from chainpy.eth.ethtype.hexbytes import EthHashBytes
from chainpy.eventbridge.utils import timestamp_msec
from prometheus_client import Counter, Gauge, Info
from chainpy.prometheus_metric import PrometheusExporter

from rbclib.consts import ChainEventStatus


class PrometheusExporterRelayer(PrometheusExporter):
    SUPPORTED_CHAINS = [ChainIndex.BIFROST, ChainIndex.ETHEREUM, ChainIndex.BINANCE, ChainIndex.POLYGON]
    START_TIME = timestamp_msec()

    REQUEST_COUNTERS: Dict[ChainEventStatus, Dict[ChainIndex, Counter]] = dict()
    INCOMPLETE_SCORE_GAUGE: Dict[ChainIndex, Gauge] = dict()
    HEARTBEAT_COUNTER = Counter("num_of_heartbeat", "Description")
    RUNNING_SESSIONS = Gauge("running_sessions", "Description")
    ASSET_PRICES: Dict[str, Gauge] = dict()
    BTC_BLOCK_HEIGHT = Gauge("latest_height_for_btc_hash", "Description")
    EXTERNAL_CHAIN_ROUND: Dict[ChainIndex, Gauge] = dict()

    @staticmethod
    def init_prometheus_exporter_on_relayer(port: int = PrometheusExporter.PROMETHEUS_SEVER_PORT):

        PrometheusExporter.init_prometheus_exporter(port)

        for chain_index in PrometheusExporterRelayer.SUPPORTED_CHAINS:
            """ add 3 when a REQUESTED is discovered. subtract 1 when the others are discovered. """
            PrometheusExporterRelayer.INCOMPLETE_SCORE_GAUGE[chain_index] = Gauge(
                "incomplete_gauge_of_{}".format(chain_index.name),
                "Description of counter"
            )

            for status in ChainEventStatus:
                if status == ChainEventStatus.NONE:
                    continue
                if PrometheusExporterRelayer.REQUEST_COUNTERS.get(status) is None:
                    PrometheusExporterRelayer.REQUEST_COUNTERS[status] = dict()
                PrometheusExporterRelayer.REQUEST_COUNTERS[status][chain_index] = Counter(
                    '{}_counter_starts_on_{}'.format(status.name, chain_index.name),
                    'Description of counter'
                )

    @staticmethod
    def exporting_request_metric(_chain_index: ChainIndex, _status: ChainEventStatus):
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return

        PrometheusExporterRelayer.REQUEST_COUNTERS[_status][_chain_index].inc()

        if _status == ChainEventStatus.ACCEPTED or _status == ChainEventStatus.REJECTED:
            # do nothing
            pass
        elif _status == ChainEventStatus.REQUESTED:
            PrometheusExporterRelayer.INCOMPLETE_SCORE_GAUGE[_chain_index].inc(2)
        else:
            PrometheusExporterRelayer.INCOMPLETE_SCORE_GAUGE[_chain_index].dec(1)

    @staticmethod
    def exporting_heartbeat_metric():
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return
        PrometheusExporterRelayer.exporting_running_time_metric()
        PrometheusExporterRelayer.HEARTBEAT_COUNTER.inc()

    @staticmethod
    def exporting_running_time_metric():
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return
        elapsed_time_minutes = (timestamp_msec() - PrometheusExporterRelayer.START_TIME) / 60000
        running_sessions = elapsed_time_minutes / 15
        PrometheusExporterRelayer.RUNNING_SESSIONS.set(running_sessions)

    @staticmethod
    def exporting_asset_prices(coin_symbols: List[str], prices: List[EthAmount]):
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return

        for symbol in coin_symbols:
            if PrometheusExporterRelayer.ASSET_PRICES.get(symbol) is None:
                PrometheusExporterRelayer.ASSET_PRICES[symbol] = Gauge("price_of_{}".format(symbol), "Description")
            price = float(prices[coin_symbols.index(symbol)].float_str)
            PrometheusExporterRelayer.ASSET_PRICES[symbol].set(price)

    @staticmethod
    def exporting_btc_hash(height: int):
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return
        PrometheusExporterRelayer.BTC_BLOCK_HEIGHT.set(height)

    @staticmethod
    def exporting_external_chain_rnd(chain_index: ChainIndex, rnd: int):
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return

        if PrometheusExporterRelayer.EXTERNAL_CHAIN_ROUND.get(chain_index) is None:
            chain_name = chain_index.name.lower()
            PrometheusExporterRelayer.EXTERNAL_CHAIN_ROUND[chain_index] = Gauge(
                "round_of_{}".format(chain_name),
                "Description"
            )
        PrometheusExporterRelayer.EXTERNAL_CHAIN_ROUND[chain_index].set(rnd)
