from typing import Optional

from bridgeconst.consts import Asset, Oracle
from chainpy.eventbridge.chaineventabc import CallParamTuple, SendParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.periodiceventabc import PeriodicEventABC
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger
from chainpy.offchain.priceaggregator import PriceOracleAgg

from rbclib.bifrostutils import is_selected_relayer
from rbclib.chainevents import NoneParams
from rbclib.metric import PrometheusExporterRelayer
from rbclib.switchable_enum import chain_primitives
from rbclib.utils import log_invalid_flow
from relayer.global_config import relayer_config_global


class PriceUpOracle(PeriodicEventABC):
    def __init__(
        self,
        manager: EventBridge,
        period_sec: int = 300,
        time_lock: int = timestamp_msec(),
        price_cli: PriceOracleAgg = None
    ):
        if period_sec == 0:
            period_sec = relayer_config_global.price_source_collection_period_sec
        super().__init__(manager, period_sec, time_lock)

        if price_cli is not None:
            self.__cli = price_cli
        else:
            self.__cli = PriceOracleAgg(relayer_config_global.price_source_url_dict)

        PrometheusExporterRelayer.exporting_running_time_metric()

    @property
    def relayer(self) -> EventBridge:
        return self.manager

    def clone_next(self):
        return self.__class__(self.relayer, self.period_sec, self.time_lock + self.period_sec * 1000, self.__cli)

    def summary(self) -> str:
        return "{}".format(self.__class__.__name__)

    def build_call_transaction_params(self) -> CallParamTuple:
        log_invalid_flow("PriceUp", self)
        return NoneParams

    def build_transaction_params(self) -> SendParamTuple:
        # check whether this is current authority
        auth = is_selected_relayer(
            self.relayer, chain_primitives.BIFROST, relayer_address=self.relayer.active_account.address
        )
        if not auth:
            return NoneParams

        # dictionary of prices (key: coin id)
        symbols = [Asset[asset_name].symbol for asset_name in relayer_config_global.price_oracle_assets]
        symbols_str = [symbol.name for symbol in symbols]
        collected_prices = self.__cli.get_current_weighted_price(symbols_str)

        # build oid list and prices list
        oid_list = [Oracle.price_oracle_from_symbol(symbol).formatted_bytes() for symbol in symbols]
        prices = [value for value in collected_prices.values()]
        PrometheusExporterRelayer.exporting_asset_prices(symbols_str, prices)

        global_logger.formatted_log(
            "PriceUp",
            address=self.relayer.active_account.address,
            related_chain_name=chain_primitives.BIFROST.name,
            msg="{}:price-feeding".format(self.__class__.__name__)
        )
        return (
            chain_primitives.BIFROST.name,
            "socket",
            "oracle_aggregate_feeding",
            [oid_list, [price.bytes() for price in prices]]
        )

    def handle_call_result(self, result: tuple) -> Optional[PeriodicEventABC]:
        log_invalid_flow("PriceUp", self)
        return None

    def handle_tx_result_success(self) -> Optional[PeriodicEventABC]:
        return None

    def handle_tx_result_fail(self) -> Optional[PeriodicEventABC]:
        log_invalid_flow("PriceUp", self)
        return None

    def handle_tx_result_no_receipt(self) -> Optional[PeriodicEventABC]:
        log_invalid_flow("PriceUp", self)
        return None
