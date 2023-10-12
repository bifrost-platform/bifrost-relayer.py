import sys
from enum import Enum
from typing import Union


class ChainEventStatus(Enum):
    NONE = 0
    REQUESTED = 1
    FAILED = 2
    EXECUTED = 3
    REVERTED = 4
    ACCEPTED = 5
    REJECTED = 6
    COMMITTED = 7
    ROLLBACKED = 8
    NEXT_AUTHORITY_RELAYED = 9
    NEXT_AUTHORITY_COMMITTED = 10

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name

    def formatted_bytes(self) -> bytes:
        return self.value.to_bytes(1, 'big')

    def formatted_hex(self) -> str:
        return "0x" + self.formatted_bytes().hex()


class ChainPrimitive(Enum):
    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def size():
        return 4

    @classmethod
    def from_bytes(cls, value: bytes):
        if len(value) != cls.size():
            raise Exception("Not matched size: actual({}), expected({})".format(len(value), cls.size()))
        return cls(int.from_bytes(value, "big"))

    def formatted_bytes(self) -> bytes:
        return self.value.to_bytes(self.size(), "big")

    @classmethod
    def str_with_size(cls):
        return cls.__name__ + "-{}".format(cls.size())


class MainnetPrimitives(ChainPrimitive):
    NONE = 0
    BIFROST = 0x0bfc
    ETHEREUM = 1
    BINANCE = 56
    MATIC = 137
    AVALANCHE = 43114
    BASE = 8453


class TestnetPrimitives(ChainPrimitive):
    NONE = 0
    BIFROST = 0xbfc0
    ETHEREUM = 5
    BINANCE = 97
    MATIC = 80001
    AVALANCHE = 43113
    BASE = 84531


ChainEnum = Union[MainnetPrimitives, TestnetPrimitives]
chain_enum = TestnetPrimitives if '--testnet' in sys.argv[1:] or '-t' in sys.argv[1:] else MainnetPrimitives
