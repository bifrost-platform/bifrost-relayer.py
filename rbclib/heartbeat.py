from typing import TYPE_CHECKING, Optional

from chainpy.eventbridge.chaineventabc import CallParamTuple, SendParamTuple
from chainpy.eventbridge.periodiceventabc import PeriodicEventABC
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger

from rbclib.metric import PrometheusExporterRelayer
from .bifrostutils import is_pulsed_hear_beat
from .chainevents import NoneParams
from .globalconfig import relayer_config_global
from .switchable_enum import SwitchableChain

if TYPE_CHECKING:
    from relayer.relayer import Relayer


class RelayerHeartBeat(PeriodicEventABC):
    def __init__(
        self,
        relayer: "Relayer",
        period_sec: int = relayer_config_global.heart_beat_period_sec,
        time_lock: int = timestamp_msec()
    ):
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
            return SwitchableChain.BIFROST.name, "relayer_authority", "heartbeat", []
        else:
            return NoneParams

    def handle_call_result(self, result: tuple) -> Optional[PeriodicEventABC]:
        return None

    def handle_tx_result_success(self) -> Optional[PeriodicEventABC]:
        PrometheusExporterRelayer.exporting_heartbeat_metric()
        global_logger.formatted_log(
            "HeartBeat",
            address=self.relayer.active_account.address,
            related_chain_name=SwitchableChain.BIFROST.name,
            msg="HeartBeat({})".format(True)
        )
        return None

    def handle_tx_result_fail(self) -> Optional[PeriodicEventABC]:
        global_logger.formatted_log(
            "HeartBeat",
            address=self.relayer.active_account.address,
            related_chain_name=SwitchableChain.BIFROST.name,
            msg="HeartBeat({})".format(False)
        )
        return None

    def handle_tx_result_no_receipt(self) -> Optional[PeriodicEventABC]:
        global_logger.formatted_log(
            "HeartBeat",
            address=self.relayer.active_account.address,
            related_chain_name=SwitchableChain.BIFROST.name,
            msg="HeartBeat({})".format(None)
        )
        return None
