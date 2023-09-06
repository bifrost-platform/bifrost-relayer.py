from typing import Optional, Tuple, Union, List

from bridgeconst.consts import ChainEventStatus, Chain, RBCMethodV1, Asset
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.hexbytes import EthHexBytes, EthAddress, EthHashBytes
from chainpy.eth.ethtype.utils import to_eth_v
from chainpy.eth.managers.eventobj import DetectedEvent
from chainpy.eventbridge.chaineventabc import ChainEventABC, CallParamTuple, SendParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger

from rbclib.events.chain_event import ChainFailedEvent, ChainRequestedEvent, ChainExecutedEvent, ChainRevertedEvent, ChainAcceptedEvent, ChainRejectedEvent, \
    ChainCommittedEvent, ChainRollbackedEvent
from rbclib.metric import PrometheusExporterRelayer
from rbclib.primitives.consts import RBC_EVENT_STATUS_START_DATA_START_INDEX, RBC_EVENT_STATUS_START_DATA_END_INDEX, NoneParams, \
    BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, SOCKET_CONTRACT_NAME, SUBMIT_FUNCTION_NAME
from rbclib.primitives.relay_chain import chain_enum
from rbclib.submits import PollSubmit
from rbclib.utils import fetch_relayer_index, log_invalid_flow, fetch_relayer_num, extract_latest_event_status
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

        if status == ChainEventStatus.ACCEPTED \
                or status == ChainEventStatus.REJECTED \
                or status == ChainEventStatus.COMMITTED \
                or status == ChainEventStatus.ROLLBACKED:
            casting_type = RbcEvent.select_child(status)
            return casting_type(detected_event, time_lock, relayer)
        else:
            return None