from abc import ABCMeta, abstractmethod
from typing import Optional, TYPE_CHECKING

from ..eth.ethtype.consts import ChainIndex
from ..eth.ethtype.hexbytes import EthHashBytes

from .chaineventabc import TaskStatus, ReceiptParams, CallParams, CallParamTuple, SendParamTuple, \
    BASIC_GAS_LIMIT_MULTIPLIER
from .utils import timestamp_msec

if TYPE_CHECKING:
    from eventbridge import EventBridge


class CollectedData:
    def __init__(self, src_id: str, data: EthHashBytes):
        self.chain_index = ChainIndex.OFFCHAIN
        self.src_id = src_id
        self.data = data


class PeriodicEventABC(metaclass=ABCMeta):
    def __init__(self, manager: "EventBridge", period_sec: int, time_lock: int = None):
        self.__period_sec = period_sec
        self.__time_lock = timestamp_msec() if time_lock is None else time_lock
        self.__manager = manager

        self.__on_chain = ChainIndex.OFFCHAIN

        self.__task_status = TaskStatus.SendTX
        self.__receipt_params: Optional[ReceiptParams] = None
        self.__call_params: Optional[CallParams] = None

    def __eq__(self, other):
        return self.time_lock == other.time_lock

    def __gt__(self, other):
        return self.time_lock > other.time_lock

    def __lt__(self, other):
        return self.time_lock < other.time_lock

    @abstractmethod
    def clone_next(self):
        pass

    @property
    def manager(self):
        return self.__manager

    @property
    def time_lock(self) -> int:
        return self.__time_lock

    @time_lock.setter
    def time_lock(self, time_lock: int):
        if not isinstance(time_lock, int):
            raise Exception("Time error")
        self.__time_lock = time_lock

    @property
    def period_sec(self) -> int:
        return self.__period_sec

    @property
    def on_chain(self) -> ChainIndex:
        return self.__on_chain

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

    def get_call_params(self) -> Optional[CallParams]:
        return self.__call_params

    def switch_to_call(self):
        self.__task_status = TaskStatus.CallTx
        self.__receipt_params = None

    def switch_to_send(self):
        self.__receipt_params = None
        self.__task_status = TaskStatus.SendTX

    def gas_limit_multiplier(self) -> float:
        return BASIC_GAS_LIMIT_MULTIPLIER

    @abstractmethod
    def summary(self) -> str:
        pass

    @abstractmethod
    def build_call_transaction_params(self) -> CallParamTuple:
        pass

    @abstractmethod
    def build_transaction_params(self) -> SendParamTuple:
        """ A method to build a transaction which handles the event """
        pass

    @abstractmethod
    def handle_call_result(self, result: tuple) -> Optional["PeriodicEventABC"]:
        pass

    @abstractmethod
    def handle_tx_result_success(self) -> Optional["PeriodicEventABC"]:
        """ A method to build the next event when the previous tx successes """
        pass

    @abstractmethod
    def handle_tx_result_fail(self) -> Optional["PeriodicEventABC"]:
        """ A method to build the next event when the previous tx fails """
        pass

    @abstractmethod
    def handle_tx_result_no_receipt(self) -> Optional["PeriodicEventABC"]:
        """ A method to build the next event when the previous tx does not have receipt """
        pass
