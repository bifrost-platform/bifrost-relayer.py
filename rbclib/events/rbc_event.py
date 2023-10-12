from typing import Optional, Tuple, Union, List

from chainpy.eth.ethtype.hexbytes import EthHexBytes, EthHashBytes
from chainpy.eth.ethtype.utils import to_eth_v
from chainpy.eth.managers.eventobj import DetectedEvent
from chainpy.eventbridge.chaineventabc import ChainEventABC, CallParamTuple, SendParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger

from rbclib.metric import PrometheusExporterRelayer
from rbclib.primitives.chain import ChainEventStatus, chain_enum, ChainEnum
from rbclib.primitives.consts import RBC_EVENT_STATUS_START_DATA_START_INDEX, RBC_EVENT_STATUS_START_DATA_END_INDEX, NoneParams, \
    BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, SOCKET_CONTRACT_NAME, SUBMIT_FUNCTION_NAME, GET_REQ_INFO_FUNCTION_NAME
from rbclib.primitives.method import RBCMethodV1
from rbclib.submits import PollSubmit
from rbclib.utils import fetch_relayer_index, log_invalid_flow, fetch_relayer_num, extract_latest_event_status, fetch_quorum, fetch_socket_rbc_sigs
from relayer.global_config import relayer_config_global, RelayerRole
from relayer.relayer import Relayer


class RbcEvent(ChainEventABC):
    """
    Data class for event from socket contract.
    """
    EVENT_NAME = "Socket"

    def __init__(self,
                 detected_event: DetectedEvent,
                 time_lock: int,
                 manager: EventBridge):
        super().__init__(detected_event, time_lock, manager)

    def __cmp__(self, other):
        return self.status.value < other.status.value

    @staticmethod
    def select_child(status: ChainEventStatus):
        child_class_map = {
            ChainEventStatus.REQUESTED: ChainRequestedEvent,
            ChainEventStatus.FAILED: ChainFailedEvent,
            ChainEventStatus.EXECUTED: ChainExecutedEvent,
            ChainEventStatus.REVERTED: ChainRevertedEvent,
            ChainEventStatus.ACCEPTED: ChainAcceptedEvent,
            ChainEventStatus.REJECTED: ChainRejectedEvent,
            ChainEventStatus.COMMITTED: ChainCommittedEvent,
            ChainEventStatus.ROLLBACKED: ChainRollbackedEvent
        }

        return child_class_map.get(status)

    @classmethod
    def init(cls, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        """ Depending on the event status, selects a child class of Socket Event, and initiates its instance. """
        # parse event-status from event data (fast, but not expandable)
        status_data = detected_event.data[RBC_EVENT_STATUS_START_DATA_START_INDEX:RBC_EVENT_STATUS_START_DATA_END_INDEX]
        status = ChainEventStatus(status_data.int())
        casting_type = RbcEvent.select_child(status)

        # The normal relayer processes the ACCEPTED or REJECTED event after a certain period of time.
        if time_lock == 0:
            # bootstrap
            return casting_type(detected_event, time_lock, manager)

        elif (relayer_config_global.relayer_role == RelayerRole.SLOW_RELAYER and
              (casting_type == ChainAcceptedEvent or casting_type == ChainRejectedEvent)):
            # slow-relayer case
            ret = casting_type(
                detected_event, time_lock + relayer_config_global.slow_relayer_delay_sec * 1000, manager
            )
            # does not export log in bootstrap process
            global_logger.formatted_log(
                "Protocol",
                address=manager.active_account.address,
                related_chain_name=chain_enum.NONE.name,
                msg="SlowRelay:{}:delay-{}-sec".format(ret.summary(), relayer_config_global.slow_relayer_delay_sec)
            )
            return ret
        else:
            return casting_type(detected_event, time_lock, manager)

    @property
    def relayer(self) -> EventBridge:
        return self.manager

    def clone_with_other_status(self, next_status: ChainEventStatus, time_lock: Optional[int] = None):
        """ clone with the specific status. """
        if time_lock is None:
            time_lock = timestamp_msec()

        # get event data and update status
        self.detected_event.data = RbcEvent.change_status_of_data(self.detected_event, next_status)

        return RbcEvent.init(self.detected_event, time_lock, self.relayer)

    def summary(self) -> str:
        """ returns summary string for logger. """
        req_id = self.req_id()
        request_id_str = [req_id[0].name, req_id[1], req_id[2]]
        return "{}:{}".format(request_id_str, self.status.name)

    def check_my_event(self) -> bool:
        if relayer_config_global.is_fast_relayer():
            return True

        if self.src_chain.name not in self.manager.supported_chain_list:
            global_logger.formatted_log(
                "WrongRequest",
                address=self.relayer.active_account.address,
                related_chain_name=self.src_chain.name,
                msg="CheckMyEvent:RequestOnNotSupportedChain: {}".format(self.summary())
            )
            return False

        cached_index = self.relayer.get_value_by_key(self.rnd)
        global_logger.formatted_log(
            "CheckAuth",
            address=self.relayer.active_account.address,
            related_chain_name=chain_enum.BIFROST.name,
            msg="CheckMyEvent:RelayerIdxCache: {}".format([(rnd, idx) for rnd, idx in self.relayer.cache.cache.items()])
        )
        if cached_index is not None:
            return True

        relayer_index = fetch_relayer_index(self.manager, chain_enum.BIFROST, rnd=self.rnd)
        global_logger.formatted_log(
            "UpdateAuth",
            address=self.relayer.active_account.address,
            related_chain_name=chain_enum.BIFROST.name,
            msg="CheckMyEvent:FetchRelayerIdx:round({}):index({})".format(self.rnd, relayer_index)
        )

        if relayer_index is not None:
            self.manager.set_value_by_key(self.rnd, relayer_index)
            return True

        global_logger.formatted_log(
            "UpdateAuth",
            address=self.relayer.active_account.address,
            related_chain_name=chain_enum.BIFROST.name,
            msg="CheckMyEvent:IgnoreRequest:{}".format(self.summary())
        )
        return False

    def build_call_transaction_params(self) -> CallParamTuple:
        """ builds and returns call transaction parameters related to this event. """
        if not self.check_my_event():
            return NoneParams
        log_invalid_flow("Protocol", self)
        return NoneParams

    def build_transaction_params(self) -> SendParamTuple:
        """ builds and returns send transaction parameters related to this event. """
        raise Exception("Not Implemented")

    def handle_call_result(self, result):
        """
        logic to be executed according to the result of call transaction built by "build_call_transaction_params"
        """
        if not self.check_my_event():
            return None
        log_invalid_flow("Protocol", self)
        return None

    def handle_tx_result_fail(self):
        """
        logic to be executed when the transaction fails.
        - fail on estimateGas rpc request for the transaction
        - zero value in transaction receipt for the transaction
        """
        if not self.check_my_event():
            return None
        log_invalid_flow("Protocol", self)
        return None

    def handle_tx_result_success(self):
        """
        logic to be executed when the transaction success.
        - one value in transaction receipt for the transaction
        """
        if not self.check_my_event():
            return None

        PrometheusExporterRelayer.exporting_request_metric(self.src_chain, self.status)

        # do nothing
        return None

    def handle_tx_result_no_receipt(self):
        """ logic to be executed when the transaction receipt does not arrive within the specified time. """
        if not self.check_my_event():
            return None
        log_invalid_flow("Protocol", self)
        return self.handle_tx_result_fail()

    def is_inbound(self) -> bool:
        return self.src_chain != chain_enum.BIFROST

    def is_outbound(self) -> bool:
        return self.src_chain == chain_enum.BIFROST

    def req_id(self) -> Tuple[ChainEnum, int, int]:
        unzipped_decoded_data = self.decoded_data[0]
        req_id_tuple = unzipped_decoded_data[0]
        return chain_enum.from_bytes(req_id_tuple[0]), req_id_tuple[1], req_id_tuple[2]

    @property
    def req_id_concat_bytes(self) -> EthHexBytes:
        chain, rnd, seq = self.req_id()
        return EthHexBytes(chain.formatted_bytes()) + EthHexBytes(rnd, 16) + EthHexBytes(seq, 16)

    @property
    def src_chain(self) -> ChainEnum:
        return self.req_id()[0]

    @property
    def rnd(self) -> int:
        return self.req_id()[1]

    @property
    def seq(self) -> int:
        return self.req_id()[2]

    @property
    def status(self) -> ChainEventStatus:
        unzipped_decoded_data = self.decoded_data[0]
        return ChainEventStatus(unzipped_decoded_data[1])

    def inst(self) -> Tuple[Union[ChainEnum, int], Union[RBCMethodV1, int]]:
        unzipped_decoded_data = self.decoded_data[0]
        inst_id_tuple = unzipped_decoded_data[2]
        return chain_enum.from_bytes(inst_id_tuple[0]), RBCMethodV1.from_bytes(inst_id_tuple[1])

    @property
    def dst_chain(self) -> ChainEnum:
        return self.inst()[0]

    @property
    def rbc_method(self) -> RBCMethodV1:
        return self.inst()[1]

    @staticmethod
    def bootstrap(manager: "Relayer", detected_events: List[DetectedEvent]) -> List['RbcEvent']:
        if manager.__class__.__name__ != "Relayer":
            raise Exception("Relayer only as a manger")

        # the collected events are made into objects and stored in the list
        rbc_events = list()
        for detected_event in detected_events:
            event_obj = RbcEvent.init(detected_event, 0, manager)
            rbc_events.append(event_obj)

        # remove finalized event objects
        not_finalized_event_objs = RbcEvent._remove_finalized_rids(rbc_events)

        # remove too late event
        not_handled_events_objs = list()

        if manager.round_cache is None:
            raise Exception("relayer's current rnd is None")
        min_rnd = manager.round_cache - BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS
        for not_finalized_event_obj in not_finalized_event_objs:
            if min_rnd > not_finalized_event_obj.rnd:
                continue

            if relayer_config_global.is_fast_relayer():
                status = not_finalized_event_obj.status
                if status != ChainEventStatus.ACCEPTED and status != ChainEventStatus:
                    continue

            not_finalized_event_obj.time_lock = timestamp_msec()
            not_handled_events_objs.append(not_finalized_event_obj)

        # logging and return not finalized event objects
        for event_obj in not_handled_events_objs:
            global_logger.formatted_log(
                "BootStrap",
                address=manager.active_account.address,
                msg="Unchecked{}Log:{}".format(RbcEvent.EVENT_NAME, event_obj.summary())
            )
        return not_handled_events_objs

    @staticmethod
    def _remove_finalized_rids(event_objs: List["RbcEvent"]) -> List["RbcEvent"]:
        # request_id_str -> event_obj with last status
        event_with_last_status_of_each_rid = dict()
        for event_obj in event_objs:
            request_id_str = event_obj.req_id_concat_bytes.hex()
            # store new event object with the rid
            if request_id_str not in event_with_last_status_of_each_rid:
                event_with_last_status_of_each_rid[request_id_str] = [event_obj]
                continue
            else:
                event_with_last_status_of_each_rid[request_id_str].append(event_obj)

        not_finalized_latest_event_objs = list()
        for rid_str, status_event_list in event_with_last_status_of_each_rid.items():
            latest_status_obj = extract_latest_event_status(status_event_list)
            if latest_status_obj.status in [ChainEventStatus.COMMITTED, ChainEventStatus.ROLLBACKED]:
                continue
            not_finalized_latest_event_objs.append(latest_status_obj)
        return not_finalized_latest_event_objs

    @staticmethod
    def change_status_of_data(detected_event: DetectedEvent, event_status: ChainEventStatus):
        data = detected_event.data
        start = RBC_EVENT_STATUS_START_DATA_START_INDEX
        end = RBC_EVENT_STATUS_START_DATA_END_INDEX
        return data[:start] + EthHashBytes(event_status.value) + data[end:]

    def is_primary_relayer(self):
        if relayer_config_global.is_fast_relayer():
            return True
        total_validator_num = fetch_relayer_num(self.relayer, chain_enum.BIFROST)

        primary_index = self.detected_event.block_number % total_validator_num
        my_index = self.relayer.get_value_by_key(self.rnd)

        return primary_index == my_index

    def build_transaction_param_with_sig(self) -> SendParamTuple:
        next_status = ChainEventStatus(self.status.value + 2)
        data_with_next_status = self.change_status_of_data(self.detected_event, next_status)
        sig = self.relayer.active_account.ecdsa_recoverable_sign(data_with_next_status)
        submit_data = PollSubmit(self).add_single_sig(sig.r, sig.s, to_eth_v(sig.v))
        return (
            chain_enum.BIFROST.name,
            SOCKET_CONTRACT_NAME,
            SUBMIT_FUNCTION_NAME,
            submit_data.submit_tuple()
        )


class ExternalRbcEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)

    @classmethod
    def init(cls, detected_event: DetectedEvent, time_lock: int, relayer: "Relayer"):
        """ Depending on the event status, selects a child class of Socket Event, and initiates its instance. """
        # parse event-status from event data (fast, but not expandable)
        status_data = detected_event.data[RBC_EVENT_STATUS_START_DATA_START_INDEX:RBC_EVENT_STATUS_START_DATA_END_INDEX]
        status = ChainEventStatus(status_data.int())

        if status in [ChainEventStatus.ACCEPTED, ChainEventStatus.REJECTED, ChainEventStatus.COMMITTED, ChainEventStatus.ROLLBACKED]:
            casting_type = RbcEvent.select_child(status)
            return casting_type(detected_event, time_lock, relayer)
        else:
            return None


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
        self, target_chain: ChainEnum, is_primary_relay: bool, chain_event_status: ChainEventStatus
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
