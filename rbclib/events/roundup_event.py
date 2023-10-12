from typing import List

import eth_abi
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHashBytes, EthHexBytes
from chainpy.eth.ethtype.utils import recursive_tuple_to_list, keccak_hash
from chainpy.eth.managers.eventobj import DetectedEvent
from chainpy.eventbridge.chaineventabc import ChainEventABC, SendParamTuple, CallParamTuple
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eventbridge.utils import timestamp_msec
from chainpy.logger import global_logger

from rbclib.primitives.chain import chain_enum, ChainEnum, ChainEventStatus
from rbclib.primitives.consts import NoneParams, SOCKET_CONTRACT_NAME, ROUND_UP_VOTING_FUNCTION_NAME
from rbclib.submits import AggregatedRoundUpSubmit
from rbclib.utils import fetch_sorted_relayer_list_lower, fetch_latest_round, fetch_socket_vsp_sigs, log_invalid_flow
from relayer.global_config import relayer_config_global


class RoundUpEvent(ChainEventABC):
    EVENT_NAME = "RoundUp"

    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: EventBridge):
        # ignore inserted time_lock, forced set to zero for handling this event with high priority
        super().__init__(detected_event, time_lock, manager)
        self.updating_chains = [chain_enum[chain] for chain in self.relayer.supported_chain_list]
        self.updating_chains.remove(chain_enum.BIFROST)
        self.selected_chain: ChainEnum = chain_enum.NONE
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

    def clone(self, selected_chain: ChainEnum):
        clone_obj = self.__class__(self.detected_event, self.time_lock, self.relayer)
        clone_obj.selected_chain = selected_chain
        return clone_obj

    def is_previous_relayer(self) -> bool:
        if relayer_config_global.is_fast_relayer():
            return True
        return self.relayer.is_in_cache(self.round - 1)

    def is_primary_relayer(self) -> bool:
        if relayer_config_global.is_fast_relayer():
            return True
        previous_validator_list = fetch_sorted_relayer_list_lower(
            self.relayer, chain_enum.BIFROST, rnd=(self.round - 1)
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
        if self.selected_chain == chain_enum.NONE:
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
            related_chain_name=chain_enum.BIFROST.name,
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
        data_to_sig = eth_abi.encode(types_str_list, [self.round, self.sorted_validator_list])
        sig_msg = keccak_hash(data_to_sig)

        return {
            "event_status": self.status,
            "validator_round": self.round,
            "validator_list": [EthAddress(addr) for addr in decoded_roundup_event[1][1]],  # self.sorted_validator_list?
            "signing_msg_hash": sig_msg,
            "signatures": [[EthHashBytes(sig[0]), EthHashBytes(sig[1]), EthHexBytes(sig[2])] for sig in sigs]
        }
