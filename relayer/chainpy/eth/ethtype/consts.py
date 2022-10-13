from enum import Enum


def sized_hex(a: int, a_size: int) -> str:
    limit = 2 ** (a_size << 3) - 1
    if a > limit:
        raise Exception("overflow")
    return "0x" + hex(a)[2:].zfill(a_size * 2)


def concat_2enum_as_int(a, b) -> int:
    a_hex, b_hex = sized_hex(a.value, a.size()), sized_hex(b.value, b.size())
    return int(a_hex + b_hex.replace("0x", ""), 16)


class EnumInterface(Enum):

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def size() -> int:
        raise Exception("Not implemented")

    def formatted_hex(self) -> str:
        return sized_hex(self.value, self.size())

    def formatted_bytes(self) -> bytes:
        return bytes.fromhex(self.formatted_hex()[2:])

    @classmethod
    def from_name(cls, name):
        return cls.__dict__[name]


class ChainIndex(EnumInterface):
    # BITCOIN-like chains
    NONE         = 0x0000000000000000
    BITCOIN      = 0x0101000000000000
    BITCOIN_CASH = 0x0102000000000000

    # ETHEREUM-like chains
    BIFROST      = 0x0201000000000000
    ETHEREUM     = 0x0202000000000000
    BINANCE      = 0x0203000000000000
    AVALANCHE    = 0x0204000000000000
    KLAYTN       = 0x0205000000000000
    POLYGON      = 0x0206000000000000

    # for oracle
    OFFCHAIN     = 0xFF00000000000000

    @staticmethod
    def size():
        return 8
