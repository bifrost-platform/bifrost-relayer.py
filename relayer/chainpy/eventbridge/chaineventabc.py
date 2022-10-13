from abc import *
from enum import Enum
from typing import Tuple, Optional, List, Dict, Union, TYPE_CHECKING

from ..eth.managers.eventhandler import DetectedEvent
from ..eth.ethtype.consts import ChainIndex
from ..eth.ethtype.hexbytes import EthHashBytes

if TYPE_CHECKING:
    from .eventbridge import EventBridge

ReceiptParamTuple = Tuple[ChainIndex, EthHashBytes]
SendParamTuple = Tuple[ChainIndex, str, str, Union[tuple, list]]
CallParamTuple = Tuple[ChainIndex, str, str, Union[tuple, list]]


BASIC_GAS_LIMIT_MULTIPLIER = 1.2


class ReceiptParams:
    def __init__(self, target_chain: ChainIndex, tx_hash: EthHashBytes):
        self.__on_chain = target_chain
        self.__tx_hash = tx_hash

    @property
    def on_chain(self) -> ChainIndex:
        return self.__on_chain

    @property
    def tx_hash(self) -> EthHashBytes:
        return self.__tx_hash

    def tuple(self) -> ReceiptParamTuple:
        return self.__on_chain, self.__tx_hash


class CallParams:
    def __init__(self, target_chain: ChainIndex, contract_name: str, method_name: str, params: Union[tuple, list]):
        self.__on_chain = target_chain
        self.__contract_name = contract_name
        self.__method_name = method_name
        self.__params = params

    def tuple(self):
        return self.__on_chain, self.__contract_name, self.__method_name, self.__params


class TaskStatus(Enum):
    SendTX = 1
    CallTx = 2
    CheckReceipt = 3


class ChainEventABC(metaclass=ABCMeta):
    def __init__(self,
                 detected_event: DetectedEvent,
                 time_lock: int,
                 manager: "EventBridge"):
        self.__detected_event = detected_event
        self.__time_lock = time_lock
        self.__manager = manager

        self.__task_status = TaskStatus.SendTX
        self.__receipt_params: Optional[ReceiptParams] = None
        self.__decoded_data = None

    @classmethod
    @abstractmethod
    def init(cls, detected_event: DetectedEvent, time_lock: int, event_bridge: "EventBridge"):
        pass

    def __eq__(self, other):
        return self.time_lock == other.time_lock

    def __gt__(self, other):
        return self.time_lock > other.time_lock

    def __lt__(self, other):
        return self.time_lock < other.time_lock

    @property
    def manager(self):
        return self.__manager

    @property
    def time_lock(self) -> int:
        return self.__time_lock

    @time_lock.setter
    def time_lock(self, time_lock: int):
        if not isinstance(time_lock, int):
            raise Exception("Time type error")
        self.__time_lock = time_lock

    @property
    def detected_event(self) -> DetectedEvent:
        return self.__detected_event

    @detected_event.setter
    def detected_event(self, detected_event: DetectedEvent):
        self.__detected_event = detected_event

    @property
    def decoded_data(self) -> tuple:
        if self.__decoded_data is None:
            self.__decoded_data = self.__manager.decode_event(self.__detected_event)
        return self.__decoded_data

    @property
    def on_chain(self) -> ChainIndex:
        return self.__detected_event.chain_index

    @property
    def task_status(self) -> TaskStatus:
        return self.__task_status

    def switch_to_check_receipt(self, target_chain: ChainIndex, tx_hash: EthHashBytes, time_lock: int):
        if not isinstance(target_chain, ChainIndex):
            raise Exception("receipt target chain: type error")
        if not isinstance(tx_hash, EthHashBytes):
            raise Exception("receipt tx_hash: type error")
        self.time_lock = time_lock
        self.__receipt_params = ReceiptParams(target_chain, tx_hash)
        self.__task_status = TaskStatus.CheckReceipt

    def get_receipt_params(self) -> Optional[ReceiptParams]:
        return self.__receipt_params

    def switch_to_call(self, time_lock: int = None):
        if time_lock is not None:
            self.time_lock = time_lock
        self.__task_status = TaskStatus.CallTx
        self.__receipt_params = None

    def switch_to_send(self, time_lock: int = None):
        if time_lock is not None:
            self.time_lock = time_lock
        self.__receipt_params = None
        self.__task_status = TaskStatus.SendTX

    def gas_limit_multiplier(self) -> float:
        return BASIC_GAS_LIMIT_MULTIPLIER

    @abstractmethod
    def summary(self) -> str:
        pass

    @abstractmethod
    def build_call_transaction_params(self) -> CallParamTuple:
        """ A method to build a call transaction """
        pass

    @abstractmethod
    def build_transaction_params(self) -> SendParamTuple:
        """ A method to build a transaction which handles the event """
        pass

    @abstractmethod
    def handle_call_result(self, result: tuple) -> Optional["ChainEventABC"]:
        pass

    @abstractmethod
    def handle_tx_result_success(self) -> Optional["ChainEventABC"]:
        """ A method to build the next event when the previous tx successes """
        pass

    @abstractmethod
    def handle_tx_result_fail(self) -> Optional["ChainEventABC"]:
        """ A method to build the next event when the previous tx fails """
        pass

    @abstractmethod
    def handle_tx_result_no_receipt(self) -> Optional["ChainEventABC"]:
        """ A method to build the next event when the previous tx does not have receipt """
        pass

    @abstractmethod
    def decoded_dict(self) -> dict:
        pass

    @staticmethod
    @abstractmethod
    def bootstrap(manager: "EventBridge", _range: Dict[ChainIndex, List[int]]) -> List['ChainEventABC']:
        """ unchecked events -erase-> remainders"""
        pass
