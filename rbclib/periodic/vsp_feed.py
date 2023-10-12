from typing import Optional

import eth_abi
from chainpy.eventbridge.chaineventabc import CallParamTuple, SendParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.periodiceventabc import PeriodicEventABC
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger

from rbclib.metric import PrometheusExporterRelayer
from rbclib.primitives.chain import chain_enum
from rbclib.primitives.consts import SOCKET_CONTRACT_NAME, ROUND_UP_FUNCTION_NAME, NoneParams
from rbclib.submits import SocketSignature
from rbclib.utils import fetch_bottom_round, fetch_latest_round, fetch_relayer_index, is_selected_relayer, fetch_sorted_relayer_list_lower, \
    log_invalid_flow
from relayer.global_config import relayer_config_global


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
            supported_chain_list.remove(chain_enum.BIFROST.name)
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
        round_from_bn = fetch_latest_round(self.relayer, chain_enum.BIFROST)

        # for prometheus exporter
        for chain_name in self.relayer.supported_chain_list:
            chain = chain_enum[chain_name]
            rnd = fetch_latest_round(self.relayer, chain)
            PrometheusExporterRelayer.exporting_external_chain_rnd(chain_name, rnd)

        global_logger.formatted_log(
            "CheckRound",
            address=self.relayer.active_account.address,
            related_chain_name=chain_enum.BIFROST.name,
            msg="VSPFeed:cached({}):fetched({})".format(self.__current_round, round_from_bn)
        )

        if self.__current_round >= round_from_bn:
            return NoneParams

        # update round cache
        self.current_round = round_from_bn

        # update relayer index cache
        relayer_index = fetch_relayer_index(self.relayer, chain_enum.BIFROST, rnd=round_from_bn)
        global_logger.formatted_log(
            "UpdateAuth",
            address=self.relayer.active_account.address,
            related_chain_name=chain_enum.BIFROST.name,
            msg="VSPFeed:FetchRelayerIdx:round({}):index({})".format(round_from_bn, relayer_index)
        )

        if relayer_index is not None:
            self.relayer.set_value_by_key(round_from_bn, relayer_index)
            global_logger.formatted_log(
                "CheckAuth",
                address=self.relayer.active_account.address,
                related_chain_name=chain_enum.BIFROST.name,
                msg="VSPFeed:UpdatedRelayerIdxCache: {}".format([(rnd, idx) for rnd, idx in self.relayer.cache.cache.items()])
            )
        else:
            global_logger.formatted_log(
                "UpdateAuth",
                address=self.relayer.active_account.address,
                related_chain_name=chain_enum.BIFROST.name,
                msg="NotValidator:round({})".format(round_from_bn)
            )

        # vote for new validator list by only previous validator
        if not is_selected_relayer(
            self.relayer, chain_enum.BIFROST,
            relayer_address=self.relayer.active_account.address,
            rnd=(round_from_bn - 1)
        ):
            return NoneParams

        # build VSP feed data with signature
        sorted_validator_list = fetch_sorted_relayer_list_lower(self.relayer, chain_enum.BIFROST)
        data_to_sig = eth_abi.encode(["uint256", "address[]"], [round_from_bn, sorted_validator_list])
        sig = self.relayer.active_account.ecdsa_recoverable_sign(data_to_sig)
        socket_sig = SocketSignature.from_single_sig(sig.r, sig.s, sig.v + 27)

        submit_data = [(round_from_bn, sorted_validator_list, socket_sig.tuple())]
        return (
            chain_enum.BIFROST.name,
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
