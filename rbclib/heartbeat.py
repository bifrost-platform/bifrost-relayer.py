import logging

from chainpy.eventbridge.periodiceventabc import PeriodicEventABC
from typing import TYPE_CHECKING, Optional

from relayer.metric import PrometheusExporterRelayer
from .bifrostutils import is_pulsed_hear_beat
from .chainevents import NoneParams
from chainpy.eth.ethtype.consts import Chain
from chainpy.eventbridge.chaineventabc import CallParamTuple, SendParamTuple
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import formatted_log, Logger

if TYPE_CHECKING:
    from relayer.relayer import Relayer


heart_beat_logger = Logger("HeartBeat", logging.INFO)


class RelayerHeartBeat(PeriodicEventABC):
    COLLECTION_PERIOD_SEC = 30

    def __init__(self,
                 relayer: "Relayer",
                 period_sec: int = 0,
                 time_lock: int = timestamp_msec()):
        if period_sec == 0:
            period_sec = self.__class__.COLLECTION_PERIOD_SEC
        super().__init__(relayer, period_sec, time_lock)

    @property
    def relayer(self) -> "Relayer":
        return self.manager

    def clone_next(self):
        return self.__class__(
            self.relayer,
            self.period_sec,
            self.time_lock + self.period_sec * 1000
        )

    def summary(self) -> str:
        return "{}".format(self.__class__.__name__)

    def build_call_transaction_params(self) -> CallParamTuple:
        return NoneParams

    def build_transaction_params(self) -> SendParamTuple:
        if not is_pulsed_hear_beat(self.relayer):
            return Chain.BFC_TEST, "relayer_authority", "heartbeat", []
        else:
            return NoneParams

    def handle_call_result(self, result: tuple) -> Optional[PeriodicEventABC]:
        return None

    def handle_tx_result_success(self) -> Optional[PeriodicEventABC]:
        PrometheusExporterRelayer.exporting_heartbeat_metric()
        formatted_log(
            heart_beat_logger,
            relayer_addr=self.relayer.active_account.address,
            log_id="HeartBeat",
            related_chain=Chain.BFC_TEST,
            log_data="HeartBeat({})".format(True)
        )
        return None

    def handle_tx_result_fail(self) -> Optional[PeriodicEventABC]:
        formatted_log(
            heart_beat_logger,
            relayer_addr=self.relayer.active_account.address,
            log_id="HeartBeat",
            related_chain=Chain.BFC_TEST,
            log_data="HeartBeat({})".format(False)
        )
        return None

    def handle_tx_result_no_receipt(self) -> Optional[PeriodicEventABC]:
        formatted_log(
            heart_beat_logger,
            relayer_addr=self.relayer.active_account.address,
            log_id="HeartBeat",
            related_chain=Chain.BFC_TEST,
            log_data="HeartBeat({})".format(None)
        )
        return None
