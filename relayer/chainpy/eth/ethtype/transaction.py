import copy
from abc import ABCMeta, abstractmethod
from typing import Optional

from .utils import *
from .hexbytes import EthAddress, EthHashBytes, EthHexBytes
from .amount import EthAmount
from .consts import ChainIndex
from ..managers.configs import FeeConfig

PRIORITY_FEE_MULTIPLIER = 4
GAS_MULTIPLIER = 1.5


class FeeParams(metaclass=ABCMeta):
    def __init__(self, chain_index: ChainIndex, count: int = -1):
        self.__chain_index = chain_index
        self.__count = count

    @property
    def count(self) -> int:
        return self.__count

    @count.setter
    def count(self, count: int):
        self.__count = count

    @property
    def chain_index(self) -> ChainIndex:
        return self.__chain_index

    @property
    @abstractmethod
    def type(self) -> int:
        pass

    @abstractmethod
    def increase_gas_fee_config(self):
        pass

    @abstractmethod
    def check_fee_upper_bound_and_commit_fee(self, gas_price: int = None, base_fee_price: int = None, priority_fee_price: int = None):
        pass

    @abstractmethod
    def dict(self) -> dict:
        pass

    @abstractmethod
    def boost_fee(self, rate: float = 1.1):
        pass


class FeeParamsType0(FeeParams):
    def __init__(self, chain_index: ChainIndex, fee_config: FeeConfig):
        super().__init__(chain_index)
        self.__fee_upper_bound = copy.deepcopy(fee_config)
        self.__committed_gas_price = None

    @property
    def type(self) -> int:
        return 0

    def increase_gas_fee_config(self):
        update_rates = self.__fee_upper_bound.fee_update_rates
        if update_rates is None:
            return self

        if isinstance(update_rates, list) and len(update_rates) > 0:
            self.count += 1
            count = min(self.count, len(update_rates) - 1)
            update_rate = update_rates[count]
            self.__fee_upper_bound.gas_price = int(self.__fee_upper_bound.gas_price * update_rate)
        return self

    def check_fee_upper_bound_and_commit_fee(self,
                                             network_gas_price: int = None,
                                             network_base_fee_price: int = None,
                                             network_priority_fee_price: int = None):
        # type check
        if network_gas_price is None:
            raise Exception("Fee type error")

        # check limit
        if self.__fee_upper_bound.gas_price < network_gas_price:
            # TODO logging?
            print("fee parameter issue: config({}) < network({})".format(
                self.__fee_upper_bound.gas_price, network_gas_price))
            return False

        self.__committed_gas_price = int(network_gas_price * GAS_MULTIPLIER)
        return True

    def boost_fee(self, rate: float = 1.1):
        if self.__committed_gas_price is not None:
            self.__committed_gas_price = int(self.__committed_gas_price * rate)

    def dict(self) -> dict:
        if self.__committed_gas_price is not None:
            return {"gasPrice": hex(self.__committed_gas_price)}
        return {}


class FeeParamsType2(FeeParams):
    def __init__(self, chain_index: ChainIndex, fee_config: FeeConfig):
        super().__init__(chain_index)
        self.__fee_config = copy.deepcopy(fee_config)
        self.__committed_max_fee_price_cache = None
        self.__committed_max_priority_price_cache = None

    @property
    def type(self) -> int:
        return 2

    def increase_gas_fee_config(self):
        update_rates = self.__fee_config.fee_update_rates
        if update_rates is None:
            return self
        if isinstance(update_rates, list) and len(update_rates) > 0:
            self.count += 1
            count = self.count if self.count >= len(update_rates) else len(update_rates) - 1
            update_rate = update_rates[count]
            self.__fee_config.max_priority_price = int(self.__fee_config.max_priority_price * update_rate)
            self.__fee_config.max_gas_price = int(self.__fee_config.max_gas_price * update_rate)
        return self

    def check_fee_upper_bound_and_commit_fee(self,
                                             network_gas_price: int = None,
                                             network_base_fee_price: int = None,
                                             network_priority_fee_price: int = None):
        if network_base_fee_price is None:
            print("none base fee price")
            return False

        if network_priority_fee_price is None:
            print("none priority fee price")
            return False

        # some chain is not allowed zero priority fee
        network_priority_fee_price = network_priority_fee_price * PRIORITY_FEE_MULTIPLIER if network_priority_fee_price > 0 else 1
        net_max_gas_price = network_priority_fee_price + network_base_fee_price
        if self.__fee_config.max_priority_price < network_priority_fee_price:
            print("fee priority fee price issue: config({}) < network({})".format(
                self.__fee_config.max_priority_price, network_priority_fee_price
            ))
            return False
        if self.__fee_config.max_gas_price < net_max_gas_price:
            print("fee max gas price issue: config({}) < network({})".format(
                self.__fee_config.max_gas_price, net_max_gas_price
            ))
            print("fee parameter issue: config({}) < network({})".format(self.__fee_config, network_gas_price))
            return False

        self.__committed_max_priority_price_cache = network_priority_fee_price
        self.__committed_max_fee_price_cache = int(net_max_gas_price * GAS_MULTIPLIER)
        return True

    def boost_fee(self, rate: float = 1.1):
        self.__committed_max_fee_price_cache = int(self.__committed_max_fee_price_cache * rate)

    def dict(self) -> dict:
        if self.__committed_max_priority_price_cache is not None and self.__committed_max_fee_price_cache is not None:
            return {
                "maxFeePerGas": hex(self.__committed_max_fee_price_cache),
                "maxPriorityFeePerGas": hex(self.__committed_max_priority_price_cache)
            }
        return {}


class SendTransaction(metaclass=ABCMeta):
    def __init__(self, chain_id: int, to_addr: EthAddress, data: EthHexBytes, value: EthAmount):
        self.__chain_id = chain_id
        self.__to_addr = to_addr
        self.__data = data
        self.__value = value

        self.__nonce = None
        self.__fee_param = None
        self.__gas_limit = None

    @property
    def nonce(self) -> Optional[int]:
        return self.__nonce

    @nonce.setter
    def nonce(self, nonce: int):
        self.__nonce = nonce

    @property
    def fee_upper_bound(self) -> Optional[FeeParams]:
        return self.__fee_param

    @fee_upper_bound.setter
    def fee_upper_bound(self, fee_params: FeeParams):
        if self.type == 0 and isinstance(fee_params, FeeParamsType2):
            raise Exception("Not matches types of Transaction and FeeParams.")
        if self.type == 2 and isinstance(fee_params, FeeParamsType0):
            raise Exception("Not matches types of Transaction and FeeParams.")
        self.__fee_param = fee_params

    @property
    def gas_limit(self) -> Optional[int]:
        return self.__gas_limit

    @gas_limit.setter
    def gas_limit(self, gas_limit: int):
        self.__gas_limit = gas_limit

    def tx_hash(self) -> EthHashBytes:
        encoded: EthHexBytes = self.serialize()
        hash_ = ETH_HASH(encoded).digest()
        return EthHashBytes(hash_)

    def boost_upper_bound(self, rate: float = 1.1):
        if self.fee_upper_bound is not None:
            self.fee_upper_bound.boost_fee(rate)

    @abstractmethod
    def serialize(self):
        # TODO implementation
        pass

    def dict(self) -> dict:
        basic_dict = {
            "to": self.__to_addr.with_checksum(),
            "value": self.__value.hex(),
            "chainId": self.__chain_id,
            "data": self.__data.hex(),
        }
        if self.__fee_param is not None:
            basic_dict.update(self.fee_upper_bound.dict())
        if self.__nonce is not None:
            basic_dict["nonce"] = self.__nonce
        if self.__gas_limit is not None:
            basic_dict["gas"] = self.__gas_limit
        return basic_dict

    def is_sendable(self) -> bool:
        return self.__nonce is not None and self.fee_upper_bound is not None and self.__gas_limit is not None

    @property
    @abstractmethod
    def type(self) -> int:
        pass


class TransactionType0(SendTransaction):
    def __init__(self, chain_id: int, to_addr: EthAddress, data: EthHexBytes, value: EthAmount):
        super().__init__(chain_id, to_addr, data, value)

    def serialize(self):
        # TODO implementation
        pass

    @property
    def type(self) -> int:
        return 0


class TransactionType2(SendTransaction):
    def __init__(self, chain_id: int, to_addr: EthAddress, data: EthHexBytes, value: EthAmount):
        super().__init__(chain_id, to_addr, data, value)

    def serialize(self):
        # TODO implementation
        pass

    @property
    def type(self) -> int:
        return 2


class CallTransaction:
    def __init__(self,
                 chain_index: ChainIndex,
                 to_addr: EthAddress,
                 data: EthHexBytes,
                 value: EthAmount = None,
                 from_addr: EthAddress = None):
        self.__chain_index = chain_index
        self.__from = from_addr
        self.__to = to_addr
        self.__data = data
        self.__value = value

    def dict(self) -> dict:
        ret_dict = {"to": self.__to.with_checksum(), "data": self.__data.hex()}
        if self.__from is not None:
            ret_dict["from"] = self.__from.with_checksum()
        if self.__value is not None:
            ret_dict["value"] = self.__value.int()
        return ret_dict

    @property
    def chain_index(self) -> ChainIndex:
        return self.__chain_index
