from typing import Optional

import eth_abi
from bridgeconst.consts import Oracle, Asset, Chain
from chainpy.btc.managers.simplerpccli import SimpleBtcClient
from chainpy.eth.ethtype.hexbytes import EthHashBytes
from chainpy.eventbridge.chaineventabc import CallParamTuple, SendParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.periodiceventabc import PeriodicEventABC
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger
from chainpy.offchain.priceaggregator import PriceOracleAgg

from rbclib.metric import PrometheusExporterRelayer
from .bifrostutils import (
    is_submitted_oracle_feed,
    fetch_oracle_latest_round,
    fetch_bottom_round,
    fetch_sorted_relayer_list_lower,
    fetch_latest_round,
    is_selected_relayer,
    fetch_relayer_index
)
from .chainevents import NoneParams, SOCKET_CONTRACT_NAME
from .globalconfig import relayer_config_global
from .relayersubmit import SocketSignature
from .switchable_enum import chain_primitives
from .utils import log_invalid_flow

CONSENSUS_ORACLE_FEEDING_FUNCTION_NAME = "oracle_consensus_feeding"
ROUND_UP_FUNCTION_NAME = "round_control_poll"


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


class BtcHashUpOracle(PeriodicEventABC):
    def __init__(
        self,
        manager: EventBridge,
        period_sec: int = 300,
        time_lock: int = timestamp_msec(),
        btc_cli: SimpleBtcClient = None
    ):
        if period_sec == 0:
            period_sec = relayer_config_global.btc_hash_source_collection_period_sec
        super().__init__(manager, period_sec, time_lock)

        self.__cli = btc_cli if btc_cli is not None else SimpleBtcClient(relayer_config_global.btc_hash_source_url, 1)

        PrometheusExporterRelayer.exporting_running_time_metric()

        self.delayed = False

    @property
    def relayer(self) -> EventBridge:
        return self.manager

    def clone_next(self):
        period_msec = self.period_sec * 1000
        time_lock = self.time_lock + period_msec // 10 if self.delayed else self.time_lock + period_msec
        return self.__class__(self.relayer, self.period_sec, time_lock, self.__cli)

    def summary(self) -> str:
        return "{}".format(self.__class__.__name__)

    def build_call_transaction_params(self) -> CallParamTuple:
        log_invalid_flow("BtcHash", self)
        return NoneParams

    def build_transaction_params(self) -> SendParamTuple:
        # check whether this is current authority
        auth = is_selected_relayer(
            self.relayer, chain_primitives.BIFROST, relayer_address=self.relayer.active_account.address
        )
        if not auth:
            return NoneParams

        latest_height_from_socket = fetch_oracle_latest_round(self.relayer, Oracle.BITCOIN_BLOCK_HASH)
        latest_height_from_chain = self.__cli.get_latest_confirmed_height()

        delta = latest_height_from_chain - latest_height_from_socket
        if delta == 0:
            return NoneParams

        if delta < 0:
            # critical error
            global_logger.formatted_log(
                "BtcHash",
                address=self.relayer.active_account.address,
                related_chain_name=chain_primitives.BIFROST.name,
                msg="oracle-error:OracleHeight({})>BtcHeight({})".format(
                    latest_height_from_socket, latest_height_from_chain
                )
            )
            return NoneParams

        self.delayed = True if delta > 1 else False

        feed_target_height = latest_height_from_socket + 1
        submitted = is_submitted_oracle_feed(self.relayer, Oracle.BITCOIN_BLOCK_HASH, feed_target_height)
        if not submitted:
            result = self.__cli.get_block_hash_by_height(feed_target_height)
            block_hash = EthHashBytes(result)
            PrometheusExporterRelayer.exporting_btc_hash(feed_target_height)
            global_logger.formatted_log(
                "BtcHash",
                address=self.manager.active_account.address,
                related_chain_name=chain_primitives.BIFROST.name,
                msg="btcHash({}):height({})".format(block_hash.hex(), feed_target_height)
            )

            return (
                chain_primitives.BIFROST.name,
                SOCKET_CONTRACT_NAME,
                CONSENSUS_ORACLE_FEEDING_FUNCTION_NAME,
                [
                    [Oracle.BITCOIN_BLOCK_HASH.formatted_bytes()],
                    [feed_target_height],
                    [block_hash.bytes()]
                ]
            )

        else:
            global_logger.formatted_log(
                "BtcHash",
                address=self.manager.active_account.address,
                related_chain_name=chain_primitives.BIFROST.name,
                msg="submitted:height({})".format(feed_target_height)
            )
            return NoneParams

    def handle_call_result(self, result: tuple) -> Optional[PeriodicEventABC]:
        log_invalid_flow("BtcHash", self)
        return None

    def handle_tx_result_success(self) -> Optional[PeriodicEventABC]:
        return None

    def handle_tx_result_fail(self) -> Optional[PeriodicEventABC]:
        log_invalid_flow("BtcHash", self)
        return None

    def handle_tx_result_no_receipt(self) -> Optional[PeriodicEventABC]:
        log_invalid_flow("BtcHash", self)
        return None

    def gas_limit_multiplier(self) -> float:
        return 2.0


class VSPFeed(PeriodicEventABC):
    def __init__(
        self,
        manager: EventBridge,
        period_sec: int = 60,
        time_lock: int = timestamp_msec(),
        _round: int = None
    ):
        if period_sec == 0:
            period_sec = relayer_config_global.validator_set_check_period_sec
        super().__init__(manager, period_sec, time_lock)
        if _round is None:
            supported_chain_list = self.relayer.supported_chain_list
            supported_chain_list.remove(chain_primitives.BIFROST.name)
        self.__current_round = fetch_bottom_round(self.relayer) if _round is None else _round

        PrometheusExporterRelayer.exporting_running_time_metric()

    @property
    def relayer(self) -> EventBridge:
        return self.manager

    @property
    def current_round(self) -> int:
        return self.__current_round

    @current_round.setter
    def current_round(self, rnd: int):
        self.__current_round = rnd

    def clone_next(self):
        return self.__class__(
            self.relayer,
            self.period_sec,
            self.time_lock + self.period_sec * 1000,
            self.current_round
        )

    def summary(self) -> str:
        return "{}".format(self.__class__.__name__)

    def build_call_transaction_params(self) -> CallParamTuple:
        log_invalid_flow("VSPFeed", self)
        return NoneParams

    def build_transaction_params(self) -> SendParamTuple:
        round_from_bn = fetch_latest_round(self.relayer, chain_primitives.BIFROST)

        # for prometheus exporter
        for chain_name in self.relayer.supported_chain_list:
            chain = Chain.from_name(chain_name)
            rnd = fetch_latest_round(self.relayer, chain)
            PrometheusExporterRelayer.exporting_external_chain_rnd(chain_name, rnd)

        global_logger.formatted_log(
            "CheckRound",
            address=self.relayer.active_account.address,
            related_chain_name=chain_primitives.BIFROST.name,
            msg="VSPFeed:cached({}):fetched({})".format(self.__current_round, round_from_bn)
        )

        if self.__current_round >= round_from_bn:
            return NoneParams

        # update round cache
        self.current_round = round_from_bn

        # update relayer index cache
        relayer_index = fetch_relayer_index(self.relayer, chain_primitives.BIFROST, rnd=round_from_bn)
        global_logger.formatted_log(
            "UpdateAuth",
            address=self.relayer.active_account.address,
            related_chain_name=chain_primitives.BIFROST.name,
            msg="VSPFeed:FetchRelayerIdx:round({}):index({})".format(round_from_bn, relayer_index)
        )

        if relayer_index is not None:
            self.relayer.set_value_by_key(round_from_bn, relayer_index)
            global_logger.formatted_log(
                "CheckAuth",
                address=self.relayer.active_account.address,
                related_chain_name=chain_primitives.BIFROST.name,
                msg="VSPFeed:UpdatedRelayerIdxCache: {}".format([(rnd, idx) for rnd, idx in self.relayer.cache.cache.items()])
            )
        else:
            global_logger.formatted_log(
                "UpdateAuth",
                address=self.relayer.active_account.address,
                related_chain_name=chain_primitives.BIFROST.name,
                msg="NotValidator:round({})".format(round_from_bn)
            )

        # vote for new validator list by only previous validator
        if not is_selected_relayer(
                self.relayer, chain_primitives.BIFROST,
                relayer_address=self.relayer.active_account.address,
                rnd=(round_from_bn - 1)
        ):
            return NoneParams

        # build VSP feed data with signature
        sorted_validator_list = fetch_sorted_relayer_list_lower(self.relayer, chain_primitives.BIFROST)
        data_to_sig = eth_abi.encode_abi(["uint256", "address[]"], [round_from_bn, sorted_validator_list])
        sig = self.relayer.active_account.ecdsa_recoverable_sign(data_to_sig)
        socket_sig = SocketSignature.from_single_sig(sig.r, sig.s, sig.v + 27)

        submit_data = [(round_from_bn, sorted_validator_list, socket_sig.tuple())]
        return (
            chain_primitives.BIFROST.name,
            SOCKET_CONTRACT_NAME,
            ROUND_UP_FUNCTION_NAME,
            submit_data
        )

    def handle_call_result(self, result: tuple) -> Optional[PeriodicEventABC]:
        log_invalid_flow("VSPFeed", self)
        return None

    def handle_tx_result_success(self) -> Optional[PeriodicEventABC]:
        return None

    def handle_tx_result_fail(self) -> Optional[PeriodicEventABC]:
        return None

    def handle_tx_result_no_receipt(self) -> Optional[PeriodicEventABC]:
        log_invalid_flow("VSPFeed", self)
        return None
