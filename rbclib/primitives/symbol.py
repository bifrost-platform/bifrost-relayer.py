from enum import Enum


class Symbol(Enum):
    """
    Name rule: symbol of the asset
    Value rule: -
    """
    NONE = 0x00
    BFC = 0x01
    BIFI = 0x02
    BTC = 0x03
    ETH = 0x04
    BNB = 0x05
    MATIC = 0x06
    AVAX = 0x07
    USDC = 0x08
    BUSD = 0x09
    USDT = 0x0a
    DAI = 0x0b
    LINK = 0x0c
    KLAY = 0x0d
    SAT = 0x0e
    WITCH = 0x0f
    P2D = 0x10
    EGG = 0x11

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def size():
        return 4

    @property
    def decimal(self):
        """ return a decimal of the asset (self) """
        return 6 if self == Symbol.USDC or self == Symbol.USDT else 18

    @classmethod
    def str_with_size(cls):
        return cls.__name__ + "-{}".format(cls.size())
