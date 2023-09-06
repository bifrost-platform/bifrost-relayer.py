from typing import Optional, Tuple

from bridgeconst.consts import ChainEventStatus, Chain
from chainpy.eth.ethtype.utils import to_eth_v
from chainpy.eth.managers.eventobj import DetectedEvent
from chainpy.eventbridge.chaineventabc import SendParamTuple, CallParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger

from rbclib.events.rbc_event import RbcEvent
from rbclib.metric import PrometheusExporterRelayer
from rbclib.primitives.consts import NoneParams, SOCKET_CONTRACT_NAME, SUBMIT_FUNCTION_NAME, GET_REQ_INFO_FUNCTION_NAME
from rbclib.primitives.relay_chain import chain_enum
from rbclib.submits import PollSubmit
from rbclib.utils import fetch_quorum, fetch_socket_rbc_sigs, log_invalid_flow
from relayer.global_config import relayer_config_global


class ChainFailedEvent(RbcEvent):
    def __init__(self,
                 detected_event: DetectedEvent,
                 time_lock: int,
                 manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.FAILED:
            raise Exception("Event status not matches")

    def build_transaction_params(self) -> SendParamTuple:
        """ A method to build a transaction which handles the event """
        if not self.check_my_event():
            return NoneParams

        # generate signature if it's needed
        if not self.is_inbound():
            return NoneParams

        msg_to_sign = self.detected_event.data
        sig = self.relayer.active_account.ecdsa_recoverable_sign(msg_to_sign)
        submit_data = PollSubmit(self).add_single_sig(sig.r, sig.s, to_eth_v(sig.v))
        return (
            chain_enum.BIFROST.name,
            SOCKET_CONTRACT_NAME,
            SUBMIT_FUNCTION_NAME,
            submit_data.submit_tuple()
        )


class ChainRequestedEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.REQUESTED:
            raise Exception("Event status not matches")

    def build_call_transaction_params(self):
        if not self.check_my_event():
            return NoneParams
        chain, rnd, seq = self.req_id()
        return (
            self.dst_chain.name,
            SOCKET_CONTRACT_NAME,
            GET_REQ_INFO_FUNCTION_NAME,
            [(chain.formatted_bytes(), rnd, seq)]
        )

    def build_transaction_params(self) -> SendParamTuple:
        """ A method to build a transaction which handles the event """
        if not self.check_my_event():
            return NoneParams

        if self.is_inbound():
            return (
                chain_enum.BIFROST.name,
                SOCKET_CONTRACT_NAME,
                SUBMIT_FUNCTION_NAME,
                PollSubmit(self).submit_tuple()
            )
        else:
            # generate signature if it's needed
            status_changed_data = RbcEvent.change_status_of_data(self.detected_event, ChainEventStatus.ACCEPTED)
            sig = self.relayer.active_account.ecdsa_recoverable_sign(status_changed_data)
            submit_data = PollSubmit(self).add_single_sig(sig.r, sig.s, to_eth_v(sig.v))
            return (
                chain_enum.BIFROST.name,
                SOCKET_CONTRACT_NAME,
                SUBMIT_FUNCTION_NAME,
                submit_data.submit_tuple()
            )

    def handle_call_result(self, result: tuple) -> Optional["RbcEvent"]:
        if not self.check_my_event():
            return None

        voting_list = result[0][0]  # voting list starts with current status
        voting_num = voting_list[self.status.value]

        # get quorum
        quorum = fetch_quorum(self.relayer, chain_enum.BIFROST, self.rnd)
        if quorum == 0:
            return None

        if voting_num >= quorum:
            global_logger.formatted_log(
                "Protocol",
                address=self.manager.active_account.address,
                related_chain_name=chain_enum.BIFROST.name,
                msg="{}:voting-num({})".format(self.summary(), voting_num)
            )
            ret = None
        else:
            global_logger.formatted_log(
                "Protocol",
                address=self.manager.active_account.address,
                related_chain_name=chain_enum.BIFROST.name,
                msg="{}:voting-num({}):change-status".format(self.summary(), voting_num)
            )
            ret = self.handle_tx_result_fail()
        return ret

    def handle_tx_result_success(self) -> Optional['RbcEvent']:
        """ transition to ChainCallAfter """
        if not self.check_my_event():
            return None

        PrometheusExporterRelayer.exporting_request_metric(self.src_chain, self.status)

        # find out chain to call
        if self.is_inbound():
            next_time_lock = self.time_lock + 1000 * relayer_config_global.rbc_event_call_delay_sec
            self.switch_to_call(next_time_lock)
            return self
        else:
            return None

    def handle_tx_result_fail(self) -> Optional['RbcEvent']:
        """ transition to REVERTED event """
        if not self.check_my_event():
            return None
        return self.clone_with_other_status(ChainEventStatus.FAILED, self.time_lock)

    def gas_limit_multiplier(self) -> float:
        if self.is_inbound():
            return 5.0
        else:
            return 1.2


class ChainExecutedEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.EXECUTED:
            raise Exception("Event status not matches")

    def build_transaction_params(self) -> SendParamTuple:
        if not self.check_my_event():
            return NoneParams
        return self.build_transaction_param_with_sig()

    def gas_limit_multiplier(self) -> float:
        if self.is_outbound():
            return 2.0
        else:
            return 1.2


class ChainRevertedEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.REVERTED:
            raise Exception("Event status not matches")

    def build_transaction_params(self) -> SendParamTuple:
        if not self.check_my_event():
            return NoneParams
        return self.build_transaction_param_with_sig()

    def gas_limit_multiplier(self) -> float:
        if self.is_outbound():
            return 2.0
        else:
            return 1.2


class _AggregatedRelayEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        self.aggregated = True

    def build_transaction_params(self) -> SendParamTuple:
        if not self.check_my_event():
            return NoneParams

        # Check if the fast relayer has already processed.
        chain_name, contract_name, method_name, params_tuple = self.build_call_transaction_params()
        result = self.relayer.world_call(chain_name, contract_name, method_name, params_tuple)
        status, expected_status = self.check_already_done(result)
        if status == expected_status:
            global_logger.formatted_log(
                "Protocol",
                address=self.relayer.active_account.address,
                related_chain_name=chain_name,
                msg="SlowRelay:{}:AlreadyProcessed".format(self.status.name)
            )
            return NoneParams

        if self.is_primary_relayer() or not self.aggregated:
            chain_to_send = self.src_chain if self.is_inbound() else self.dst_chain
            return self.aggregated_relay(chain_to_send, self.aggregated, self.status)

        else:
            next_time_lock = self.time_lock + 1000 * relayer_config_global.rbc_event_call_delay_sec
            self.switch_to_call(next_time_lock)
            self.relayer.queue.enqueue(self)

            return NoneParams

    def build_call_transaction_params(self) -> CallParamTuple:
        if not self.check_my_event():
            return NoneParams
        target_chain = self.src_chain if self.is_inbound() else self.dst_chain
        chain, rnd, seq = self.req_id()
        return (
            target_chain.name,
            SOCKET_CONTRACT_NAME,
            GET_REQ_INFO_FUNCTION_NAME,
            [(chain.formatted_bytes(), rnd, seq)]
        )

    def check_already_done(self, result: tuple) -> Tuple[ChainEventStatus, ChainEventStatus]:
        status = ChainEventStatus(result[0][0][0])

        if self.status == ChainEventStatus.ACCEPTED:
            expected_status = ChainEventStatus.COMMITTED if self.is_inbound() else ChainEventStatus.EXECUTED
        else:
            expected_status = ChainEventStatus.ROLLBACKED if self.is_inbound() else ChainEventStatus.REVERTED

        return status, expected_status

    def handle_call_result(self, result: tuple):
        if not self.check_my_event():
            return None

        status, expected_status = self.check_already_done(result)

        if status == expected_status:
            return None
        global_logger.formatted_log(
            "Protocol",
            address=self.manager.active_account.address,
            related_chain_name=self.src_chain.name if self.is_inbound() else self.dst_chain.name,
            msg="{}:{}-thRelayer:expected({}):actual({})".format(
                self.summary(),
                self.relayer.get_latest_value(),
                expected_status.name,
                status.name
            )
        )

        self.aggregated = False
        self.switch_to_send(timestamp_msec())
        return self

    def aggregated_relay(
        self, target_chain: Chain, is_primary_relay: bool, chain_event_status: ChainEventStatus
    ) -> SendParamTuple:
        relayer_index = self.relayer.get_value_by_key(self.rnd)
        chain, rnd, seq = self.req_id()
        sigs = fetch_socket_rbc_sigs(self.relayer, (chain.formatted_bytes(), rnd, seq), chain_event_status)
        submit_data = PollSubmit(self).add_tuple_sigs(sigs)

        msg = "Primary" if is_primary_relay else "Secondary"
        global_logger.formatted_log(
            "Protocol",
            address=self.manager.active_account.address,
            related_chain_name=target_chain.name,
            msg="{}:{}-Vote({})".format(
                self.summary(),
                msg,
                relayer_index if not relayer_config_global.is_fast_relayer() else "FAST"
            )
        )
        return (
            target_chain.name,
            SOCKET_CONTRACT_NAME,
            SUBMIT_FUNCTION_NAME,
            submit_data.submit_tuple()
        )


class ChainAcceptedEvent(_AggregatedRelayEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.ACCEPTED:
            raise Exception("Event status not matches")

    def handle_tx_result_fail(self) -> Optional['ChainRejectedEvent']:
        if not self.check_my_event():
            return None
        if self.is_inbound():
            log_invalid_flow("Protocol", self)
            return None
        # outbound case
        clone_event = self.clone_with_other_status(ChainEventStatus.REJECTED, self.time_lock)
        clone_event.aggregated = False
        return clone_event


class ChainRejectedEvent(_AggregatedRelayEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.REJECTED:
            raise Exception("Event status not matches")
        self.aggregated = True


class _FinalStatusEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)

    def build_transaction_params(self) -> SendParamTuple:
        if not self.check_my_event():
            return NoneParams
        PrometheusExporterRelayer.exporting_request_metric(self.src_chain, self.status)
        return NoneParams


class ChainCommittedEvent(_FinalStatusEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.COMMITTED:
            raise Exception("Event status not matches")


class ChainRollbackedEvent(_FinalStatusEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.ROLLBACKED:
            raise Exception("Event status not matches")
