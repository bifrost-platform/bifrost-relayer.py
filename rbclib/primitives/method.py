from enum import Enum
from typing import List, Tuple, cast

from rbclib.utils import to_even_hex, concat_as_int


class OPCode(Enum):
    NONE = 0x00
    WARP = 0x01
    UNIFY = 0x02
    SPLIT = 0x03
    UNIFY_SPLIT = 0x04
    DEPOSIT = 0x05
    WITHDRAW = 0x06
    BORROW = 0x07
    REPAY = 0x08
    X_OPEN = 0x09
    X_END = 0x0a
    SWAP = 0x0b
    CALL = 0x0c

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name


    @staticmethod
    def size() -> int:
        return 1

    @classmethod
    def str_with_size(cls):
        return cls.__name__ + "-{}".format(cls.size())


class RBCMethodDirection(Enum):
    NONE = 0x00
    INBOUND = 0x01
    OUTBOUND = 0x02
    IN_AND_OUTBOUND = 0x03

    @staticmethod
    def size() -> int:
        return OPCode.size()

    @classmethod
    def str_with_size(cls):
        return cls.__name__ + "-{}".format(cls.size())


RBC_METHOD_LENGTH_SIZE = 1


class RBCMethodV1(Enum):
    NONE = 0x0000000000000000
    # INBOUND **********************************************************************************************************
    WARP_IN = concat_as_int(2, RBCMethodDirection.INBOUND, OPCode.WARP)

    WARP_UNIFY = concat_as_int(3, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY)
    WARP_UNIFY_SPLIT = concat_as_int(3, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT)

    WARP_UNIFY_DEPOSIT = concat_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.DEPOSIT)
    WARP_UNIFY_SPLIT_DEPOSIT = concat_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT, OPCode.DEPOSIT)

    WARP_UNIFY_REPAY = concat_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.REPAY)
    WARP_UNIFY_SPLIT_REPAY = concat_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT, OPCode.REPAY)

    WARP_UNIFY_SWAP = concat_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.SWAP)
    WARP_UNIFY_SPLIT_SWAP = concat_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT, OPCode.SWAP)

    WARP_UNIFY_XOPEN = concat_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.X_OPEN)
    WARP_UNIFY_SPLIT_XOPEN = concat_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT, OPCode.X_OPEN)

    WARP_CALL = concat_as_int(3, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.CALL)

    # OUTBOUND *********************************************************************************************************
    WARP_OUT = concat_as_int(2, RBCMethodDirection.OUTBOUND, OPCode.WARP)

    SPLIT_WARP = concat_as_int(3, RBCMethodDirection.OUTBOUND, OPCode.SPLIT, OPCode.WARP)
    UNIFY_SPLIT_WARP = concat_as_int(3, RBCMethodDirection.OUTBOUND, OPCode.UNIFY_SPLIT, OPCode.WARP)

    BORROW_SPLIT_WARP = concat_as_int(4, RBCMethodDirection.OUTBOUND, OPCode.BORROW, OPCode.SPLIT, OPCode.WARP)
    BORROW_UNIFY_SPLIT_WARP = concat_as_int(
        4, RBCMethodDirection.OUTBOUND, OPCode.BORROW, OPCode.UNIFY_SPLIT, OPCode.WARP
    )

    WITHDRAW_SPLIT_WARP = concat_as_int(4, RBCMethodDirection.OUTBOUND, OPCode.WITHDRAW, OPCode.SPLIT, OPCode.WARP)
    WITHDRAW_UNIFY_SPLIT_WARP = concat_as_int(
        4, RBCMethodDirection.OUTBOUND, OPCode.WITHDRAW, OPCode.UNIFY_SPLIT, OPCode.WARP
    )

    SWAP_SPLIT_WARP = concat_as_int(4, RBCMethodDirection.OUTBOUND, OPCode.SWAP, OPCode.SPLIT, OPCode.WARP)
    SWAP_UNIFY_SPLIT_WARP = concat_as_int(
        4, RBCMethodDirection.OUTBOUND, OPCode.SWAP, OPCode.UNIFY_SPLIT, OPCode.WARP
    )

    XEND_SPLIT_WARP = concat_as_int(
        4, RBCMethodDirection.OUTBOUND, OPCode.X_END, OPCode.SPLIT, OPCode.WARP
    )
    XEND_UNIFY_SPLIT_WARP = concat_as_int(
        4, RBCMethodDirection.OUTBOUND, OPCode.X_END, OPCode.UNIFY_SPLIT, OPCode.WARP
    )

    CALL_WARP = concat_as_int(3, RBCMethodDirection.OUTBOUND, OPCode.CALL, OPCode.WARP)

    # IN_AND_OUT BOUND *************************************************************************************************
    WARP_SWAP_WARP = concat_as_int(
        4, RBCMethodDirection.IN_AND_OUTBOUND, OPCode.WARP, OPCode.SWAP, OPCode.WARP
    )
    # 1-1 exchange with Unified Token contract
    WARP_UNIFY_SPLIT_WARP = concat_as_int(
        4, RBCMethodDirection.IN_AND_OUTBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT, OPCode.WARP
    )
    # in-and-out bound swap (from a token to the other token)
    WARP_UNIFY_SWAP_SPLIT_WARP = concat_as_int(
        6, RBCMethodDirection.IN_AND_OUTBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.SWAP, OPCode.SPLIT, OPCode.WARP
    )
    # in-and-out bound swap (from the BFC to a token)
    WARP_UNIFY_SPLIT_SWAP_SPLIT_WARP = concat_as_int(
        6, RBCMethodDirection.IN_AND_OUTBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT, OPCode.SWAP, OPCode.SPLIT, OPCode.WARP
    )
    # in-and-out bound swap (from a token to the BFC)
    WARP_UNIFY_SWAP_UNIFY_SPLIT_WARP = concat_as_int(
        6, RBCMethodDirection.IN_AND_OUTBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.SWAP, OPCode.UNIFY_SPLIT, OPCode.WARP
    )

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [
            "LENGTH-1",
            RBCMethodDirection.str_with_size(),
            "DYNAMIC_SIZE_ARRAY[{}]".format(OPCode.str_with_size())]

    @staticmethod
    def size():
        return 16

    def formatted_hex(self) -> str:
        if self == self.__class__.NONE:
            return "0x" + "00" * self.size()

        hex_without_0x = to_even_hex(self.value).replace("0x", "")
        op_num = int(hex_without_0x[:RBC_METHOD_LENGTH_SIZE * 2], 16)
        zero_pad = "00" * (self.size() - op_num * OPCode.size() - RBC_METHOD_LENGTH_SIZE)
        return "0x" + hex_without_0x + zero_pad

    def formatted_bytes(self) -> bytes:
        return bytes.fromhex(self.formatted_hex().replace("0x", ""))

    def analyze(self) -> Tuple[int, RBCMethodDirection, List[OPCode]]:
        self_hex = self.formatted_hex().replace("0x", "")
        len_op, direction, self_hex = int(self_hex[:2], 16), RBCMethodDirection(int(self_hex[2:4])), self_hex[4:]

        op_code_list = list()
        for i in range(len_op - 1):
            parsed_int = int(self_hex[:OPCode.size() * 2], 16)
            self_hex = self_hex[OPCode.size() * 2:]
            op_code_list.append(OPCode(parsed_int))

        if self.size() - len_op - 1 - len(self_hex) // 2 != 0:
            raise Exception("Wrong enum value")

        return len_op, direction, op_code_list

    @property
    def len_prefix(self) -> int:
        return self.analyze()[0]

    @property
    def direction(self) -> RBCMethodDirection:
        return cast(RBCMethodDirection, self.analyze()[1])

    @property
    def opcodes(self) -> List[OPCode]:
        return self.analyze()[2]

    @classmethod
    def from_bytes(cls, value: bytes):
        len_op = int.from_bytes(value[:1], "big")
        return cls(int.from_bytes(value[:len_op + 1], "big"))

    @classmethod
    def from_components(cls, direction: RBCMethodDirection, op_codes: List[OPCode]):
        return cls(concat_as_int(len(op_codes) + 1, direction, op_codes))
