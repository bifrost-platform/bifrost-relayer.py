from typing import Optional

from bridgeconst.consts import Oracle
from chainpy.btc.managers.simplerpccli import SimpleBtcClient
from chainpy.eth.ethtype.hexbytes import EthHashBytes
from chainpy.eventbridge.chaineventabc import CallParamTuple, SendParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.periodiceventabc import PeriodicEventABC
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger

from rbclib.utils import is_selected_relayer, fetch_oracle_latest_round, is_submitted_oracle_feed, log_invalid_flow
from rbclib.chainevents import NoneParams
from rbclib.consts import SOCKET_CONTRACT_NAME, CONSENSUS_ORACLE_FEEDING_FUNCTION_NAME
from rbclib.metric import PrometheusExporterRelayer
from rbclib.switchable_enum import chain_primitives
from relayer.global_config import relayer_config_global


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
