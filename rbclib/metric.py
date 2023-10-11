from typing import List

from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.prometheus_metric import PrometheusExporter
from prometheus_client import Counter, Gauge

from primitives.enums import ChainEventStatus, ChainEnum
from rbclib.primitives.consts import HEARTBEAT_COUNTER_QUERY_NAME, RUNNING_SESSIONS_QUERY_NAME, INCOMPLETE_GAUGE_QUERY_NAME, BTC_HEIGHT_QUERY_NAME, \
    ASSET_PRICES_QUERY_NAME, CHAIN_ROUNDS_QUERY_NAME, REQUEST_COUNTERS_QUERY_NAME


class PrometheusExporterRelayer(PrometheusExporter):
    START_TIME = timestamp_msec()

    HEARTBEAT_COUNTER = Counter(HEARTBEAT_COUNTER_QUERY_NAME, 'Description')
    RUNNING_SESSIONS = Gauge(RUNNING_SESSIONS_QUERY_NAME, 'Description')
    INCOMPLETE_SCORE_GAUGE = Gauge(INCOMPLETE_GAUGE_QUERY_NAME, 'Description of counter', ['chain'])

    BTC_HEIGHT = Gauge(BTC_HEIGHT_QUERY_NAME, 'Description')
    ASSET_PRICES = Gauge(ASSET_PRICES_QUERY_NAME, 'Description', ['symbol'])

    CHAIN_ROUNDS = Gauge(CHAIN_ROUNDS_QUERY_NAME, 'Description', ['chain'])
    REQUEST_COUNTERS = Counter(REQUEST_COUNTERS_QUERY_NAME, 'Description of counter', ['status'])

    @staticmethod
    def init_prometheus_exporter_on_relayer(
        supported_chains: List[str], port: int = PrometheusExporter.PROMETHEUS_SEVER_PORT
    ):
        PrometheusExporter.init_prometheus_exporter(port)

        for chain in supported_chains:
            """ add 2 when a REQUESTED is discovered. subtract 1 when the others are discovered. """
            PrometheusExporterRelayer.INCOMPLETE_SCORE_GAUGE.labels(chain.upper()).set(0)

        ignored = [
            ChainEventStatus.NONE,
            ChainEventStatus.NEXT_AUTHORITY_RELAYED,
            ChainEventStatus.NEXT_AUTHORITY_COMMITTED
        ]
        for status in (set(ChainEventStatus) - set(ignored)):
            PrometheusExporterRelayer.REQUEST_COUNTERS.labels(status.name).inc(0)

    @staticmethod
    def exporting_request_metric(chain: ChainEnum, status: ChainEventStatus):
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return

        PrometheusExporterRelayer.REQUEST_COUNTERS.labels(status.name).inc()

        ignored = [
            ChainEventStatus.NONE,
            ChainEventStatus.ACCEPTED,
            ChainEventStatus.REJECTED,
            ChainEventStatus.NEXT_AUTHORITY_RELAYED,
            ChainEventStatus.NEXT_AUTHORITY_COMMITTED
        ]
        if status in ignored:
            # do nothing
            pass
        elif status == ChainEventStatus.REQUESTED:
            PrometheusExporterRelayer.INCOMPLETE_SCORE_GAUGE.labels(chain.name.lower()).inc(2)
        else:
            PrometheusExporterRelayer.INCOMPLETE_SCORE_GAUGE.labels(chain.name.lower()).dec(1)

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
            price = float(prices[coin_symbols.index(symbol)].float_str)
            PrometheusExporterRelayer.ASSET_PRICES.labels(symbol).set(price)

    @staticmethod
    def exporting_btc_hash(height: int):
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return
        PrometheusExporterRelayer.BTC_HEIGHT.set(height)

    @staticmethod
    def exporting_external_chain_rnd(chain: str, rnd: int):
        if not PrometheusExporterRelayer.PROMETHEUS_ON:
            return
        PrometheusExporterRelayer.CHAIN_ROUNDS.labels(chain.lower()).set(rnd)
