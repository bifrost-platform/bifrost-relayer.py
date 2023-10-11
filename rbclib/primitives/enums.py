import sys
from enum import Enum
from typing import Union


class Oracle(Enum):
    ETH = 0x0100010000000000000000000000000000000000000000000000000000000004.to_bytes(32, 'big')
    BFC = 0x0100010000000000000000000000000000000000000000000000000000000001.to_bytes(32, 'big')
    BNB = 0x0100010000000000000000000000000000000000000000000000000000000005.to_bytes(32, 'big')
    MATIC = 0x0100010000000000000000000000000000000000000000000000000000000006.to_bytes(32, 'big')
    USDC = 0x0100010000000000000000000000000000000000000000000000000000000008.to_bytes(32, 'big')
    USDT = 0x010001000000000000000000000000000000000000000000000000000000000a.to_bytes(32, 'big')
    BIFI = 0x0100010000000000000000000000000000000000000000000000000000000002.to_bytes(32, 'big')
    DAI = 0x010001000000000000000000000000000000000000000000000000000000000b.to_bytes(32, 'big')

    BITCOIN_BLOCK_HASH = 0x0200020000000000000000000000000000000000000000000000000000000003.to_bytes(32, 'big')


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

    def formatted_bytes(self) -> bytes:
        return self.value.to_bytes(1, 'big')

    def formatted_hex(self) -> str:
        return "0x" + self.formatted_bytes().hex()


class ChainPrimitive(Enum):
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
