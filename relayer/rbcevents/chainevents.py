import logging
from typing import Optional, Union, Tuple, TYPE_CHECKING, Dict, List

import eth_abi

from .consts import RBCMethodIndex, TokenStreamIndex, ChainEventStatus
from .relayersubmit import PollSubmit, AggregatedRoundUpSubmit
from .utils import *
from ..chainpy.eventbridge.chaineventabc import ChainEventABC
from ..chainpy.eventbridge.multichainmonitor import bootstrap_logger
from ..chainpy.eventbridge.utils import timestamp_msec, transaction_commit_time_sec

from ..chainpy.eth.managers.eventobj import DetectedEvent
from ..chainpy.eth.ethtype.amount import EthAmount
from ..chainpy.eth.ethtype.consts import ChainIndex
from ..chainpy.eth.ethtype.hexbytes import EthAddress, EthHashBytes, EthHexBytes
from ..chainpy.eth.ethtype.utils import recursive_tuple_to_list, ETH_HASH

from ..chainpy.logger import Logger, formatted_log

if TYPE_CHECKING:
    from relayer.relayer import Relayer


proto_logger = Logger("Protocol", logging.DEBUG)

RangesDict = Dict[ChainIndex, Tuple[int, int]]
NoneParams = (ChainIndex.NONE, "", "", [])


RBC_EVENT_STATUS_START_DATA_START_INDEX = 128
RBC_EVENT_STATUS_START_DATA_END_INDEX = 160

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
    CALL_DELAY_SEC = 600
    EVENT_NAME = "Socket"

    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)

    def __cmp__(self, other):
        return self.status.value < other.status.value

    @classmethod
    def init(cls, detected_event: DetectedEvent, time_lock: int, relayer: "Relayer"):
        """ Depending on the event status, selects a child class of Socket Event, and initiates its instance. """

        # parse event-status from event data (fast, but not expandable)
        status_data = detected_event.data[RBC_EVENT_STATUS_START_DATA_START_INDEX:RBC_EVENT_STATUS_START_DATA_END_INDEX]
        status_name = ChainEventStatus(status_data.int()).name.lower().capitalize()

        casting_type = eval("Chain{}Event".format(status_name))
        return casting_type(detected_event, time_lock, relayer)

    @property
    def relayer(self) -> "Relayer":
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
        req_id = self.req_id(True)
        request_id_str = [req_id[0].name, req_id[1], req_id[2]]
        return "{}:{}".format(request_id_str, self.status.name)

    def build_call_transaction_params(self) -> Tuple[ChainIndex, str, str, Union[tuple, list]]:
        """ builds and returns call transaction parameters related to this event. """
        if not self.check_my_event():
            return NoneParams
        log_invalid_flow(proto_logger, self)
        return NoneParams

    def build_transaction_params(self):
        """ builds and returns send transaction parameters related to this event. """
        raise Exception("Not Implemented")

    def handle_call_result(self, result):
        """
        logic to be executed according to the result of call transaction built by "build_call_transaction_params"
        """
        if not self.check_my_event():
            return None
        log_invalid_flow(proto_logger, self)
        return None

    def handle_tx_result_fail(self):
        """
        logic to be executed when the transaction fails.
        - fail on estimateGas rpc request for the transaction
        - zero value in transaction receipt for the transaction
        """
        if not self.check_my_event():
            return None
        log_invalid_flow(proto_logger, self)
        return None

    def handle_tx_result_success(self):
        """
        logic to be executed when the transaction success.
        - one value in transaction receipt for the transaction
        """
        if not self.check_my_event():
            return None
        # do nothing
        return None

    def handle_tx_result_no_receipt(self):
        """ logic to be executed when the transaction receipt does not arrive within the specified time. """
        if not self.check_my_event():
            return None
        log_invalid_flow(proto_logger, self)
        return self.handle_tx_result_fail()

    def is_inbound(self) -> bool:
        return self.src_chain_index != ChainIndex.BIFROST

    def is_outbound(self) -> bool:
        return self.src_chain_index == ChainIndex.BIFROST

    def req_id(self, obj_flag: bool = False) -> Tuple[Union[int, ChainIndex], int, int]:
        unzipped_decoded_data = self.decoded_data[0]
        req_id_tuple = unzipped_decoded_data[0]
        if not obj_flag:
            return req_id_tuple
        return ChainIndex(req_id_tuple[0]), req_id_tuple[1], req_id_tuple[2]

    @property
    def req_id_str(self) -> str:
        req_id_tuple = self.req_id(False)
        req_id_bytes = EthHashBytes(req_id_tuple[0]) + EthHashBytes(req_id_tuple[1]) + EthHashBytes(req_id_tuple[2])
        return req_id_bytes.hex()

    @property
    def src_chain_index(self) -> ChainIndex:
        return self.req_id(True)[0]

    @property
    def rnd(self) -> int:
        return self.req_id(True)[1]

    @property
    def seq(self) -> int:
        return self.req_id(True)[2]

    @property
    def status(self) -> ChainEventStatus:
        unzipped_decoded_data = self.decoded_data[0]
        return ChainEventStatus(unzipped_decoded_data[1])

    @property
    def unique_id_str(self) -> str:
        req_id_tuple = self.req_id(False)
        req_id_bytes = EthHashBytes(req_id_tuple[0]) + EthHashBytes(req_id_tuple[1]) + EthHashBytes(req_id_tuple[2])
        return (req_id_bytes + EthHashBytes(self.status.value)).hex()

    def inst(self, obj_flag: bool = False) -> Tuple[Union[ChainIndex, int], Union[RBCMethodIndex, int]]:
        unzipped_decoded_data = self.decoded_data[0]
        inst_id_tuple = unzipped_decoded_data[2]
        if not obj_flag:
            return inst_id_tuple
        return ChainIndex(inst_id_tuple[0]), RBCMethodIndex(inst_id_tuple[1])

    @property
    def dst_chain_index(self) -> ChainIndex:
        return self.inst(True)[0]

    @property
    def method_index(self) -> RBCMethodIndex:
        return self.inst(True)[1]

    @property
    def method_params(self) -> Tuple[
        TokenStreamIndex, TokenStreamIndex, EthAddress, EthAddress, EthAmount, EthHexBytes
    ]:
        unzipped_decoded_data = self.decoded_data[0]
        params_tuple = unzipped_decoded_data[3]
        return (
            TokenStreamIndex(params_tuple[0]),
            TokenStreamIndex(params_tuple[1]),
            EthAddress(params_tuple[2]),
            EthAddress(params_tuple[3]),
            EthAmount(params_tuple[4]),
            EthHexBytes(params_tuple[5])
        )

    def check_my_event(self) -> bool:
        if self.src_chain_index not in self.manager.supported_chain_list:
            return False

        relayer_index = self.relayer.get_value_by_key(self.rnd)
        return relayer_index is not None

    def decoded_dict(self):
        method_params = self.method_params
        return {
            "req_id": {
                "src_chain": self.src_chain_index,
                "round": self.rnd,
                "seq_num": self.seq
            },
            "event_status": self.status,
            "instruction": {
                "dst_chain": self.dst_chain_index,
                "method": self.method_index
            },
            "action_params": {
                "token_idx1": method_params[0],
                "token_idx2": method_params[1],
                "from_addr": method_params[2],
                "to_addr": method_params[3],
                "amount": method_params[4],
                "reserved": method_params[5],
            }
        }

    @staticmethod
    def bootstrap(manager: "Relayer", _range: Dict[ChainIndex, List[int]]) -> List['RbcEvent']:
        # Announcing the start of the event collection
        formatted_log(
            bootstrap_logger,
            relayer_addr=manager.active_account.address,
            log_id="Collect{}Logs".format(RbcEvent.EVENT_NAME),
            related_chain=ChainIndex.NONE,
            log_data="range({})".format(_range)
        )

        # collect events on every chains
        events_raw = manager.collect_unchecked_multichain_event_in_range(RbcEvent.EVENT_NAME, _range)

        # the collected events are made into objects and stored in the list
        events = list()
        for event in events_raw:
            event_obj = RbcEvent.init(event, timestamp_msec(), manager)
            events.append(event_obj)

        # remove finalized event objects
        not_finalized_event_objs = RbcEvent._remove_finalized_rids(events)

        # remove too late event
        not_handled_events_obj = list()
        min_rnd = manager.valid_min_rnd
        for not_finalized_event_obj in not_finalized_event_objs:
            if min_rnd > not_finalized_event_obj.rnd:
                continue
            not_handled_events_obj.append(not_finalized_event_obj)

        # logging and return not finalized event objects
        for event_obj in not_handled_events_obj:
            formatted_log(
                bootstrap_logger,
                relayer_addr=manager.active_account.address,
                log_id="Unchecked{}Log".format(RbcEvent.EVENT_NAME),
                related_chain=ChainIndex.NONE,
                log_data=event_obj.summary()
            )
        return not_finalized_event_objs

    @staticmethod
    def _remove_finalized_rids(event_objs: List["RbcEvent"]) -> List["RbcEvent"]:
        # request_id_str -> event_obj with last status
        event_with_last_status_of_each_rid = dict()
        for event_obj in event_objs:
            request_id_str = event_obj.req_id_str
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
        total_validator_num = self.relayer.fetch_validator_num(ChainIndex.BIFROST)

        primary_index = self.detected_event.block_number % total_validator_num
        my_index = self.relayer.get_value_by_key(self.rnd)

        return primary_index == my_index

    def aggregated_relay(self, target_chain: ChainIndex, is_primary_relay: bool):
        relayer_index = self.relayer.get_value_by_key(self.rnd)
        sigs = self.relayer.fetch_socket_rbc_sigs(ChainIndex.BIFROST, self.req_id())
        submit_data = PollSubmit(self).add_tuple_sigs(sigs)

        msg = "Aggregated" if is_primary_relay else "Total"
        formatted_log(
            proto_logger,
            relayer_addr=self.manager.active_account.address,
            log_id=self.summary(),
            related_chain=target_chain,
            log_data=msg + "-Vote({})".format(relayer_index)
        )
        return target_chain, SOCKET_CONTRACT_NAME, SUBMIT_FUNCTION_NAME, submit_data.submit_tuple()

    def build_transaction_param_with_sig(self):
        next_status = ChainEventStatus(self.status.value + 2)
        data_with_next_status = self.change_status_of_data(self.detected_event, next_status)
        sig = self.relayer.active_account.ecdsa_recoverable_sign(data_with_next_status)
        submit_data = PollSubmit(self).add_single_sig(sig.r, sig.s, sig.v)
        return ChainIndex.BIFROST, SOCKET_CONTRACT_NAME, SUBMIT_FUNCTION_NAME, submit_data.submit_tuple()


class ChainRequestedEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.REQUESTED:
            raise Exception("Event status not matches")

    def build_call_transaction_params(self):
        if not self.check_my_event():
            return NoneParams
        return self.dst_chain_index, SOCKET_CONTRACT_NAME, GET_REQ_INFO_FUNCTION_NAME, [self.req_id(False)]

    def build_transaction_params(self) -> Tuple[ChainIndex, str, str, list]:
        """ A method to build a transaction which handles the event """
        if not self.check_my_event():
            return NoneParams

        if self.is_inbound():
            return ChainIndex.BIFROST, SOCKET_CONTRACT_NAME, SUBMIT_FUNCTION_NAME, PollSubmit(self).submit_tuple()  # TODO inbound forced fail
        else:
            # generate signature if it's needed
            status_changed_data = RbcEvent.change_status_of_data(self.detected_event, ChainEventStatus.ACCEPTED)
            sig = self.relayer.active_account.ecdsa_recoverable_sign(status_changed_data)
            submit_data = PollSubmit(self).add_single_sig(sig.r, sig.s, sig.v)
            return ChainIndex.BIFROST, SOCKET_CONTRACT_NAME, SUBMIT_FUNCTION_NAME, submit_data.submit_tuple()

    def handle_call_result(self, result: tuple):
        if not self.check_my_event():
            return None

        voting_list = result[0][0]  # voting list starts with current status
        voting_num = voting_list[self.status.value]

        # get quorum
        quorum = self.relayer.fetch_quorum(ChainIndex.BIFROST, self.rnd)
        if quorum == 0:
            return None

        if voting_num >= quorum:
            formatted_log(
                proto_logger,
                relayer_addr=self.manager.active_account.address,
                log_id=self.summary(),
                related_chain=ChainIndex.BIFROST,
                log_data="voting-num({})".format(voting_num)
            )
            ret = None
        else:
            formatted_log(
                proto_logger,
                relayer_addr=self.manager.active_account.address,
                log_id=self.summary(),
                related_chain=ChainIndex.BIFROST,
                log_data="voting-num({}):change-status".format(voting_num)
            )
            ret = self.handle_tx_result_fail()
        return ret

    def handle_tx_result_success(self) -> Optional['RbcEvent']:
        """ transition to ChainCallAfter """
        if not self.check_my_event():
            return None

        # find out chain to call
        if self.is_inbound():
            next_time_lock = self.time_lock + 1000 * RbcEvent.CALL_DELAY_SEC
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
                 manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.FAILED:
            raise Exception("Event status not matches")

    def build_transaction_params(self) -> Tuple[ChainIndex, str, str, Union[tuple, list]]:
        """ A method to build a transaction which handles the event """
        if not self.check_my_event():
            return NoneParams

        # generate signature if it's needed
        if not self.is_inbound():
            return NoneParams

        msg_to_sign = self.detected_event.data
        sig = self.relayer.active_account.ecdsa_recoverable_sign(msg_to_sign)
        submit_data = PollSubmit(self).add_single_sig(sig.r, sig.s, sig.v)
        return ChainIndex.BIFROST, SOCKET_CONTRACT_NAME, SUBMIT_FUNCTION_NAME, submit_data.submit_tuple()


class ChainExecutedEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.EXECUTED:
            raise Exception("Event status not matches")

    def build_transaction_params(self) -> Tuple[ChainIndex, str, str, Union[tuple, list]]:
        if not self.check_my_event():
            return NoneParams
        return self.build_transaction_param_with_sig()

    def gas_limit_multiplier(self) -> float:
        if self.is_outbound():
            return 2.0
        else:
            return 1.2


class ChainRevertedEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.REVERTED:
            raise Exception("Event status not matches")

    def build_transaction_params(self) -> Tuple[ChainIndex, str, str, Union[tuple, list]]:
        if not self.check_my_event():
            return NoneParams
        return self.build_transaction_param_with_sig()

    def gas_limit_multiplier(self) -> float:
        if self.is_outbound():
            return 2.0
        else:
            return 1.2


class ChainAcceptedEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.ACCEPTED:
            raise Exception("Event status not matches")
        self.aggregated = True

    def build_transaction_params(self) -> Tuple[ChainIndex, str, str, Union[tuple, list]]:
        if not self.check_my_event():
            return NoneParams

        if self.is_primary_relayer() or not self.aggregated:
            chain_to_send = self.src_chain_index if self.is_inbound() else self.dst_chain_index
            return self.aggregated_relay(chain_to_send, self.aggregated)

        else:
            next_time_lock = self.time_lock + 1000 * RbcEvent.CALL_DELAY_SEC
            self.switch_to_call(next_time_lock)
            self.relayer.queue.enqueue(self)

            return NoneParams

    def build_call_transaction_params(self):
        if not self.check_my_event():
            return NoneParams
        target_chain = self.src_chain_index if self.is_inbound() else self.dst_chain_index
        return target_chain, SOCKET_CONTRACT_NAME, GET_REQ_INFO_FUNCTION_NAME, [self.req_id()]

    def handle_call_result(self, result: tuple):
        if not self.check_my_event():
            return None
        status = ChainEventStatus(result[0][0][0])

        if self.is_inbound():
            commit_or_rollback = (status == ChainEventStatus.COMMITTED) or (status == ChainEventStatus.ROLLBACKED)
            total_send_flag = True if not commit_or_rollback else False
        else:
            executed_or_reverted = (status == ChainEventStatus.EXECUTED) or (status == ChainEventStatus.REVERTED)
            total_send_flag = True if not executed_or_reverted else False

        if total_send_flag:
            expected_status = ChainEventStatus.COMMITTED if self.is_inbound() else ChainEventStatus.EXECUTED
            formatted_log(
                proto_logger,
                relayer_addr=self.manager.active_account.address,
                log_id=self.summary(),
                related_chain=self.src_chain_index if self.is_inbound() else self.dst_chain_index,
                log_data="{}-thRelayer:expected({}):actual({})".format(
                    self.relayer.get_latest_value(),
                    expected_status.name,
                    status.name
                )
            )

            self.aggregated = False
            self.switch_to_send(timestamp_msec())
            return self
        else:
            return None

    def handle_tx_result_fail(self) -> Optional['ChainRejectedEvent']:
        if not self.check_my_event():
            return None
        if self.is_inbound():
            log_invalid_flow(proto_logger, self)
            return None
        # outbound case
        clone_event = self.clone_with_other_status(ChainEventStatus.REJECTED, self.time_lock)
        clone_event.aggregated = False
        return clone_event


class ChainRejectedEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.REJECTED:
            raise Exception("Event status not matches")
        self.aggregated = True

    def build_transaction_params(self) -> Tuple[ChainIndex, str, str, Union[tuple, list]]:
        if not self.check_my_event():
            return NoneParams

        if self.is_primary_relayer() or not self.aggregated:
            chain_to_send = self.src_chain_index if self.is_inbound() else self.dst_chain_index
            return self.aggregated_relay(chain_to_send, self.aggregated)

        else:
            next_time_lock = self.time_lock + 1000 * RbcEvent.CALL_DELAY_SEC
            self.switch_to_call(next_time_lock)
            self.relayer.queue.enqueue(self)

            return NoneParams

    def build_call_transaction_params(self):
        if not self.check_my_event():
            return NoneParams
        target_chain = self.src_chain_index if self.is_inbound() else self.dst_chain_index
        return target_chain, SOCKET_CONTRACT_NAME, GET_REQ_INFO_FUNCTION_NAME, [self.req_id()]

    def handle_call_result(self, result: tuple):
        if not self.check_my_event():
            return None
        status = ChainEventStatus(result[0][0][0])
        if self.is_inbound():
            commit_or_rollback = (status == ChainEventStatus.COMMITTED) or (status == ChainEventStatus.ROLLBACKED)
            total_send_flag = True if not commit_or_rollback else False
        else:
            executed_or_reverted = (status == ChainEventStatus.EXECUTED) or (status == ChainEventStatus.REVERTED)
            total_send_flag = True if not executed_or_reverted else False

        if total_send_flag:
            expected_status = ChainEventStatus.ROLLBACKED if self.is_inbound() else ChainEventStatus.REVERTED
            formatted_log(
                proto_logger,
                relayer_addr=self.manager.active_account.address,
                log_id=self.summary(),
                related_chain=self.src_chain_index if self.is_inbound() else self.dst_chain_index,
                log_data="{}-thRelayer:SwitchPrimary:expected({}):actual({})".format(
                    self.relayer.get_latest_value(),
                    expected_status.name,
                    status.name
                )
            )

            self.aggregated = False
            self.switch_to_send(timestamp_msec())
            return self
        else:
            return None


class _FinalStatusEvent(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)

    def build_transaction_params(self) -> Tuple[ChainIndex, str, str, Union[tuple, list]]:
        if not self.check_my_event():
            return NoneParams
        return NoneParams


class ChainCommittedEvent(_FinalStatusEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.COMMITTED:
            raise Exception("Event status not matches")


class ChainRollbackedEvent(_FinalStatusEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)
        if self.status != ChainEventStatus.ROLLBACKED:
            raise Exception("Event status not matches")


class ValidatorSetUpdatedEvent(ChainEventABC):
    CALL_DELAY_SEC = 200
    EVENT_NAME = "RoundUp"

    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        # ignore inserted time_lock, forced set to zero for handling this event with high priority
        super().__init__(detected_event, 0, manager)
        self.updating_chains = self.relayer.supported_chain_list
        self.updating_chains.remove(ChainIndex.BIFROST)
        self.selected_chain = None
        self.aggregated = True

    @classmethod
    def init(cls, detected_event: DetectedEvent, time_lock: int, relayer: "Relayer"):
        # ignore inserted time_lock, forced set to zero for handling this event with high priority
        return cls(detected_event, 0, relayer)

    @property
    def relayer(self) -> "Relayer":
        return self.manager

    def clone(self, selected_chain: ChainIndex):
        clone_obj = self.__class__(self.detected_event, self.time_lock, self.relayer)
        clone_obj.selected_chain = selected_chain
        return clone_obj

    def update_auth(self, new_rnd: int, validator_list: List[EthAddress]):
        # address of this relayer
        this_addr = self.relayer.active_account.address.hex().lower()
        this_addr = EthAddress(this_addr)

        # addresses of validators
        sorted_validator_list = sorted(validator_list)

        # set self as a privileged relayer in the round
        if this_addr in sorted_validator_list and self.relayer.get_value_by_key(new_rnd) is None:
            new_index = sorted_validator_list.index(this_addr)
            self.relayer.set_value_by_key(new_rnd, new_index)
            prev_index = self.relayer.get_value_by_key(new_rnd - 1)
            formatted_log(
                proto_logger,
                relayer_addr=self.relayer.active_account.address,
                log_id="UpdateRelayerIndex",
                related_chain=ChainIndex.NONE,
                log_data="from({}):to({})".format(prev_index, new_index)
            )

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

    def is_previous_relayer(self):
        return self.relayer.has_key(self.round - 1)

    def build_transaction_params(self) -> Tuple[ChainIndex, str, str, Union[tuple, list]]:
        # ignore event except one with status: 10
        if self.status != ChainEventStatus.NEXT_AUTHORITY_COMMITTED:
            return NoneParams

        # update auth cache
        self.update_auth(self.round, self.sorted_validator_list)

        # check whether this relayer is included in the very previous validator set
        if not self.is_previous_relayer():
            return NoneParams

        # split task for each native chain
        if self.selected_chain is None:
            for chain_index in self.updating_chains:
                self.relayer.queue.enqueue(self.clone(chain_index))
            return NoneParams

        # check to need to sync validator list to the selected chain
        target_round = self.relayer.fetch_validator_round(self.selected_chain)
        if target_round >= self.round:
            return NoneParams

        # code branch: primary(send) vs secondary(call)
        previous_validator_list = self.relayer.fetch_sorted_previous_validator_list(ChainIndex.BIFROST, self.round - 1)

        previous_validator_list = [EthAddress(addr) for addr in previous_validator_list]
        previous_validator_set_size = len(previous_validator_list)

        primary_index = self.detected_event.block_number % previous_validator_set_size
        if primary_index == self.relayer.get_value_by_key(self.round - 1) or not self.aggregated:
            # primary relayer do
            result = self.relayer.fetch_socket_vsp_sigs(ChainIndex.BIFROST, self.round)
            submit_data = AggregatedRoundUpSubmit(self).add_tuple_sigs(result)
            return self.selected_chain, SOCKET_CONTRACT_NAME, ROUND_UP_VOTING_FUNCTION_NAME, submit_data.submit_tuple()
        else:
            # secondary relayer do (prepare to call after a few minutes)
            next_time_lock = timestamp_msec() \
                             + transaction_commit_time_sec(self.selected_chain, self.relayer.root_config) \
                             + 1000 * ValidatorSetUpdatedEvent.CALL_DELAY_SEC
            self.switch_to_call(next_time_lock)
            self.relayer.queue.enqueue(self)

            return NoneParams

    def build_call_transaction_params(self):
        return self.selected_chain, RELAYER_AUTHORITY_CONTRACT_NAME, GET_ROUND_FUNCTION_NAME, []

    def handle_call_result(self, result):
        selected_chain_round = result[0]  # unzip
        if selected_chain_round < self.round:
            formatted_log(
                proto_logger,
                relayer_addr=self.relayer.active_account.address,
                log_id=self.__class__.__name__,
                related_chain=self.selected_chain,
                log_data="{}-thRelayer:SwitchPrimary".format(self.relayer.get_value_by_key(self.round))
            )

            self.switch_to_send(0)
            self.aggregated = False
            return self
        return None

    def handle_tx_result_success(self):
        return None

    def handle_tx_result_fail(self) -> None:
        log_invalid_flow(proto_logger, self)
        return None

    def handle_tx_result_no_receipt(self) -> None:
        log_invalid_flow(proto_logger, self)
        return None

    def summary(self) -> str:
        return "{}:{}".format(self.detected_event.event_name, self.round)

    @staticmethod
    def bootstrap(manager: "Relayer", _range: Dict[ChainIndex, List[int]]) -> List['ChainEventABC']:
        # Announcing the start of the event collection
        event_name = ValidatorSetUpdatedEvent.EVENT_NAME
        target_chain = ChainIndex.BIFROST
        formatted_log(
            bootstrap_logger,
            relayer_addr=manager.active_account.address,
            log_id="Collect{}Logs".format(event_name),
            related_chain=ChainIndex.NONE,
            log_data="range({})".format(_range[target_chain])
        )

        # collect events on only bifrost network
        chain_manager = manager.get_chain_manager_of(target_chain)
        from_block, to_block = _range[target_chain][0], _range[target_chain][1]
        events_raw = chain_manager.collect_target_event_in_range(event_name, from_block, to_block)

        # remove event object except target status event object
        target_event_objects = list()
        for event in events_raw:
            event_obj = ValidatorSetUpdatedEvent.init(event, 0, manager)
            if event_obj.status == ChainEventStatus.NEXT_AUTHORITY_COMMITTED:
                target_event_objects.append((event_obj.round, event_obj))

        latest_event_object = sorted(target_event_objects)[-1][1] if target_event_objects else None
        formatted_log(
            bootstrap_logger,
            relayer_addr=manager.active_account.address,
            log_id="Unchecked{}Log".format(event_name),
            related_chain=ChainIndex.BIFROST,
            log_data="{}".format(
                latest_event_object.summary() if latest_event_object is not None else ""
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
        _round = decoded_roundup_event[1][0]
        sorted_validator_list = sorted([EthAddress(addr) for addr in decoded_roundup_event[1][1]])
        data_to_sig = eth_abi.encode_abi(types_str_list, [_round, sorted_validator_list])
        sig_msg = EthHashBytes(ETH_HASH(data_to_sig).digest())

        return {
            "event_status": ChainEventStatus(decoded_roundup_event[0]),
            "validator_round": _round,
            "validator_list": [EthAddress(addr) for addr in decoded_roundup_event[1][1]],
            "signing_msg_hash": sig_msg,
            "signatures": [[EthHashBytes(sig[0]), EthHashBytes(sig[1]), EthHexBytes(sig[2])] for sig in sigs]
        }
