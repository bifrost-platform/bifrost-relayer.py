from typing import Optional, Union, Tuple, Dict, List

import eth_abi
from bridgeconst.consts import RBCMethodV1, ChainEventStatus, Asset, Chain
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHashBytes, EthHexBytes
from chainpy.eth.ethtype.utils import recursive_tuple_to_list, keccak_hash, to_eth_v
from chainpy.eth.managers.eventobj import DetectedEvent
from chainpy.eventbridge.chaineventabc import ChainEventABC, CallParamTuple, SendParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger

from rbclib.metric import PrometheusExporterRelayer
from relayer.relayer import Relayer
from .bifrostutils import (
    fetch_socket_vsp_sigs,
    fetch_socket_rbc_sigs,
    fetch_quorum,
    fetch_relayer_num,
    fetch_latest_round, fetch_sorted_relayer_list_lower, fetch_relayer_index
)
from .consts import (
    BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS,
    RBC_EVENT_STATUS_START_DATA_START_INDEX,
    RBC_EVENT_STATUS_START_DATA_END_INDEX
)
from .globalconfig import relayer_config_global, RelayerRole
from .relayersubmit import PollSubmit, AggregatedRoundUpSubmit
from .switchable_enum import chain_primitives
from .utils import log_invalid_flow

RangesDict = Dict[Chain, Tuple[int, int]]
NoneParams = ("", "", "", [])

SOCKET_CONTRACT_NAME = "socket"
SUBMIT_FUNCTION_NAME = "poll"
GET_REQ_INFO_FUNCTION_NAME = "get_request"
ROUND_UP_VOTING_FUNCTION_NAME = "round_control_relay"

AUTHORITY_CONTRACT_NAME = "authority"
RELAYER_AUTHORITY_CONTRACT_NAME = "relayer_authority"
GET_ROUND_FUNCTION_NAME = "latest_round"


def sorting_by_status(arr: List["RbcEvent"]) -> List["RbcEvent"]:
    ret_arr = list()
    for element in arr:
        ret_arr.append((element.status.value, element))
    return [item_tuple[1] for item_tuple in sorted(ret_arr)]


def extract_latest_status(arr: List["RbcEvent"]):
    sorted_list = sorting_by_status(arr)
    status_list = [element.status for element in sorted_list]

    inbound = sorted_list[0].is_inbound()
    if inbound:
        return sorted_list[-1]
    else:
        if ChainEventStatus.COMMITTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.COMMITTED)]
        elif ChainEventStatus.ROLLBACKED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.ROLLBACKED)]
        elif ChainEventStatus.EXECUTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.EXECUTED)]
        elif ChainEventStatus.REVERTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.REVERTED)]
        elif ChainEventStatus.ACCEPTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.ACCEPTED)]
        elif ChainEventStatus.REJECTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.REJECTED)]
        elif ChainEventStatus.REQUESTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.REQUESTED)]
        elif ChainEventStatus.FAILED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.REQUESTED)]
        else:
            raise Exception("Invalid event status")


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

        elif relayer_config_global.relayer_role == RelayerRole.SLOW_RELAYER \
                and (casting_type == ChainAcceptedEvent or casting_type == ChainRejectedEvent):
            # slow-relayer case
            ret = casting_type(
                detected_event, time_lock + relayer_config_global.slow_relayer_delay_sec * 1000, manager
            )
            # does not export log in bootstrap process
            global_logger.formatted_log(
                "Protocol",
                address=manager.active_account.address,
                related_chain_name=chain_primitives.NONE.name,
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
            related_chain_name=chain_primitives.BIFROST.name,
            msg="CheckMyEvent:RelayerIdxCache: {}".format([(rnd, idx) for rnd, idx in self.relayer.cache.cache.items()])
        )
        if cached_index is not None:
            return True

        relayer_index = fetch_relayer_index(self.manager, chain_primitives.BIFROST, rnd=self.rnd)
        global_logger.formatted_log(
            "UpdateAuth",
            address=self.relayer.active_account.address,
            related_chain_name=chain_primitives.BIFROST.name,
            msg="CheckMyEvent:FetchRelayerIdx:round({}):index({})".format(self.rnd, relayer_index)
        )

        if relayer_index is not None:
            self.manager.set_value_by_key(self.rnd, relayer_index)
            return True

        global_logger.formatted_log(
            "UpdateAuth",
            address=self.relayer.active_account.address,
            related_chain_name=chain_primitives.BIFROST.name,
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
        return self.src_chain != chain_primitives.BIFROST

    def is_outbound(self) -> bool:
        return self.src_chain == chain_primitives.BIFROST

    def req_id(self) -> Tuple[Chain, int, int]:
        unzipped_decoded_data = self.decoded_data[0]
        req_id_tuple = unzipped_decoded_data[0]
        return Chain.from_bytes(req_id_tuple[0]), req_id_tuple[1], req_id_tuple[2]

    @property
    def req_id_concat_bytes(self) -> EthHexBytes:
        chain, rnd, seq = self.req_id()
        return EthHexBytes(chain.formatted_bytes()) + EthHexBytes(rnd, 16) + EthHexBytes(seq, 16)

    @property
    def src_chain(self) -> Chain:
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

    def inst(self) -> Tuple[Union[Chain, int], Union[RBCMethodV1, int]]:
        unzipped_decoded_data = self.decoded_data[0]
        inst_id_tuple = unzipped_decoded_data[2]
        return Chain.from_bytes(inst_id_tuple[0]), RBCMethodV1.from_bytes(inst_id_tuple[1])

    @property
    def dst_chain(self) -> Chain:
        return self.inst()[0]

    @property
    def rbc_method(self) -> RBCMethodV1:
        return self.inst()[1]

    @property
    def method_params(self) -> Tuple[
        Asset, Asset, EthAddress, EthAddress, EthAmount, EthHexBytes
    ]:
        unzipped_decoded_data = self.decoded_data[0]
        params_tuple = unzipped_decoded_data[3]
        return (
            Asset.from_bytes(params_tuple[0]),
            Asset.from_bytes(params_tuple[1]),
            EthAddress(params_tuple[2]),
            EthAddress(params_tuple[3]),
            EthAmount(params_tuple[4]),
            EthHexBytes(params_tuple[5])
        )

    def decoded_dict(self):
        method_params = self.method_params
        return {
            "req_id": {
                "src_chain": self.src_chain.name,
                "round": self.rnd,
                "seq_num": self.seq
            },
            "event_status": self.status,
            "instruction": {
                "dst_chain": self.dst_chain.name,
                "method": self.rbc_method
            },
            "action_params": {
                "asset1": method_params[0],
                "asset2": method_params[1],
                "from": method_params[2],
                "to": method_params[3],
                "amount": method_params[4],
                "variants": method_params[5],
            }
        }

    def decoded_json(self):
        method_params = self.method_params
        return {
            "req_id": {
                "src_chain": self.src_chain.name,
                "round": self.rnd,
                "seq_num": self.seq
            },
            "event_status": self.status.name,
            "instruction": {
                "dst_chain": self.dst_chain.name,
                "method": self.rbc_method.name
            },
            "action_params": {
                "asset1": method_params[0].name,
                "asset2": method_params[1].name,
                "from": method_params[2].with_checksum(),
                "to": method_params[3].with_checksum(),
                "amount": method_params[4].int(),
                "variants": method_params[5].hex_without_0x(),
            }
        }

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
            latest_status_obj = extract_latest_status(status_event_list)
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
        total_validator_num = fetch_relayer_num(self.relayer, chain_primitives.BIFROST)

        primary_index = self.detected_event.block_number % total_validator_num
        my_index = self.relayer.get_value_by_key(self.rnd)

        return primary_index == my_index

    def build_transaction_param_with_sig(self) -> SendParamTuple:
        next_status = ChainEventStatus(self.status.value + 2)
        data_with_next_status = self.change_status_of_data(self.detected_event, next_status)
        sig = self.relayer.active_account.ecdsa_recoverable_sign(data_with_next_status)
        submit_data = PollSubmit(self).add_single_sig(sig.r, sig.s, to_eth_v(sig.v))
        return (
            chain_primitives.BIFROST.name,
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
                chain_primitives.BIFROST.name,
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
                chain_primitives.BIFROST.name,
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
        quorum = fetch_quorum(self.relayer, chain_primitives.BIFROST, self.rnd)
        if quorum == 0:
            return None

        if voting_num >= quorum:
            global_logger.formatted_log(
                "Protocol",
                address=self.manager.active_account.address,
                related_chain_name=chain_primitives.BIFROST.name,
                msg="{}:voting-num({})".format(self.summary(), voting_num)
            )
            ret = None
        else:
            global_logger.formatted_log(
                "Protocol",
                address=self.manager.active_account.address,
                related_chain_name=chain_primitives.BIFROST.name,
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
            chain_primitives.BIFROST.name,
            SOCKET_CONTRACT_NAME,
            SUBMIT_FUNCTION_NAME,
            submit_data.submit_tuple()
        )


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


class RoundUpEvent(ChainEventABC):
    EVENT_NAME = "RoundUp"

    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        # ignore inserted time_lock, forced set to zero for handling this event with high priority
        super().__init__(detected_event, time_lock, manager)
        self.updating_chains = [Chain[chain] for chain in self.relayer.supported_chain_list]
        self.updating_chains.remove(chain_primitives.BIFROST)
        self.selected_chain: Chain = Chain.NONE
        self.aggregated = True

    @classmethod
    def init(cls, detected_event: DetectedEvent, time_lock: int, relayer: EventBridge):
        # ignore inserted time_lock, forced set to zero for handling this event with high priority

        if time_lock == 0 or relayer_config_global.is_fast_relayer():
            # in the case of bootstrap
            return cls(detected_event, 0, relayer)
        else:
            # does not export log in bootstrap process
            global_logger.formatted_log(
                "Protocol",
                address=relayer.active_account.address,
                msg="SlowRelay:{}:delay-{}-sec".format(
                    cls.EVENT_NAME, relayer_config_global.slow_relayer_delay_sec
                )
            )
            time_lock = timestamp_msec() + relayer_config_global.slow_relayer_delay_sec * 1000
            return cls(detected_event, time_lock, relayer)

    @property
    def relayer(self) -> "EventBridge":
        return self.manager

    @property
    def status(self) -> ChainEventStatus:
        return ChainEventStatus(self.decoded_data[0])

    @property
    def round(self) -> int:
        return self.decoded_data[1][0]

    @property
    def sorted_validator_list(self) -> list:
        validator_list = self.decoded_data[1][1]
        validator_obj_list = [EthAddress(addr) for addr in validator_list]
        return sorted(validator_obj_list)

    def clone(self, selected_chain: Chain):
        clone_obj = self.__class__(self.detected_event, self.time_lock, self.relayer)
        clone_obj.selected_chain = selected_chain
        return clone_obj

    def is_previous_relayer(self) -> bool:
        if relayer_config_global.is_fast_relayer():
            return True
        return self.relayer.has_key(self.round - 1)

    def is_primary_relayer(self) -> bool:
        if relayer_config_global.is_fast_relayer():
            return True
        previous_validator_list = fetch_sorted_relayer_list_lower(
            self.relayer, chain_primitives.BIFROST, rnd=(self.round - 1)
        )
        previous_validator_list = [EthAddress(addr) for addr in previous_validator_list]
        primary_index = self.detected_event.block_number % len(previous_validator_list)
        return primary_index == self.relayer.get_value_by_key(self.round - 1)

    def build_transaction_params(self) -> SendParamTuple:
        # ignore event except one with status: 10
        if self.status != ChainEventStatus.NEXT_AUTHORITY_COMMITTED:
            return NoneParams

        # check whether this relayer is included in the very previous validator set
        if not self.is_previous_relayer():
            return NoneParams

        # split task for each native chain
        if self.selected_chain == Chain.NONE:
            for chain in self.updating_chains:
                self.relayer.queue.enqueue(self.clone(chain))
            return NoneParams

        # check to need to sync validator list to the selected chain
        target_round = fetch_latest_round(self.relayer, self.selected_chain)

        if target_round >= self.round:
            global_logger.formatted_log(
                "Protocol",
                address=self.relayer.active_account.address,
                related_chain_name=self.selected_chain.name,
                msg="SlowRelay:{}:round({}):AlreadyProcessed".format(self.__class__.EVENT_NAME, target_round)
            )
            return NoneParams

        # code branch: primary(send) vs secondary(call)
        if self.is_primary_relayer() or not self.aggregated:
            # primary relayer do
            result = fetch_socket_vsp_sigs(self.relayer, self.round)
            submit_data = AggregatedRoundUpSubmit(self).add_tuple_sigs(result)
            return (
                self.selected_chain.name,
                SOCKET_CONTRACT_NAME,
                ROUND_UP_VOTING_FUNCTION_NAME,
                submit_data.submit_tuple()
            )
        else:
            # secondary relayer do (prepare to call after a few minutes)
            next_time_lock = timestamp_msec() \
                             + self.relayer.get_chain_manager_of(self.selected_chain.name).tx_commit_time_sec \
                             + 1000 * relayer_config_global.roundup_event_call_delay_sec

            self.switch_to_send(next_time_lock)
            self.aggregated = False
            self.relayer.queue.enqueue(self)

            return NoneParams

    def build_call_transaction_params(self) -> CallParamTuple:
        pass

    def handle_call_result(self, result):
        pass

    def handle_tx_result_success(self):
        return None

    def handle_tx_result_fail(self) -> None:
        log_invalid_flow("Protocol", self)
        return None

    def handle_tx_result_no_receipt(self) -> None:
        log_invalid_flow("Protocol", self)
        return None

    def summary(self) -> str:
        return "{}:{}".format(self.detected_event.event_name, self.round)

    @staticmethod
    def bootstrap(manager: EventBridge, detected_events: List[DetectedEvent]) -> List['ChainEventABC']:
        # remove event object except target status event object
        target_event_objects = list()
        for detected_event in detected_events:
            event_obj = RoundUpEvent.init(detected_event, 0, manager)
            if event_obj.status == ChainEventStatus.NEXT_AUTHORITY_COMMITTED:
                target_event_objects.append((event_obj.round, event_obj))

        latest_event_object = sorted(target_event_objects)[-1][1] if target_event_objects else None

        global_logger.formatted_log(
            "Bootstrap",
            address=manager.active_account.address,
            related_chain_name=chain_primitives.BIFROST.name,
            msg="Unchecked{}Log:{}".format(
                RoundUpEvent.EVENT_NAME, latest_event_object.summary() if latest_event_object is not None else ""
            )
        )

        return [latest_event_object] if latest_event_object is not None else []

    def decoded_dict(self):
        decoded_roundup_event = self.decoded_data
        decoded_sigs = recursive_tuple_to_list(decoded_roundup_event[1][2])
        sigs = list()
        for i in range(len(decoded_sigs[0])):
            r, s, v = decoded_sigs[0][i], decoded_sigs[1][i], decoded_sigs[2][i]
            sigs.append([r, s, v])

        types_str_list = ["uint256", "address[]"]
        data_to_sig = eth_abi.encode_abi(types_str_list, [self.round, self.sorted_validator_list])
        sig_msg = keccak_hash(data_to_sig)

        return {
            "event_status": self.status,
            "validator_round": self.round,
            "validator_list": [EthAddress(addr) for addr in decoded_roundup_event[1][1]],  # self.sorted_validator_list?
            "signing_msg_hash": sig_msg,
            "signatures": [[EthHashBytes(sig[0]), EthHashBytes(sig[1]), EthHexBytes(sig[2])] for sig in sigs]
        }
