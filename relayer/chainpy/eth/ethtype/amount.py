import unittest
from typing import Literal, List, Union

from .utils import float_to_wei, is_dec, is_hex, to_hex_str_with_0x
from .exceptions import *


class EthAmount:
    def __init__(self, amount: Union[bytes, bytearray, float, str, int], decimal: int = 18):
        self.__decimal = decimal
        if isinstance(amount, bytes) or isinstance(amount, bytearray):
            amount_hex = to_hex_str_with_0x(amount)
            self.__amount = int(amount_hex, 16)
        elif isinstance(amount, str) and amount.count(".") == 1:
            # float string ex) "13.1234"
            float_amount = float(amount)
            self.__amount = float_to_wei(float_amount, decimal)
        elif isinstance(amount, str) and is_hex(amount):
            # hexadecimal string ex) "0xb7aa63a16fe84000"
            self.__amount = int(amount, 16)
        elif isinstance(amount, str) and is_dec(amount):
            # decimal string ex) 123456
            self.__amount = int(amount, 10)
        elif isinstance(amount, float):
            # float ex) 13.2345
            self.__amount = float_to_wei(amount, decimal)
        elif isinstance(amount, int):
            # int(wei) 13234500000000000000
            if amount < 0:
                raise EthNegativeValueError(amount)
            self.__amount = amount
        else:
            raise Exception("Not allowed amount type: {}".format(type(amount)))

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        amount_str = str(self.__amount)
        return "{}({}.{}, {})".format(
            class_name,
            amount_str[:-self.__decimal],
            amount_str[-self.__decimal:].zfill(self.__decimal),
            self.__decimal
        )

    def __add__(self, other):
        if not isinstance(other, EthAmount):
            raise EthCompareTypeError(EthAmount, type(other))
        elif self.__decimal != other.__decimal:
            raise Exception("Not matches decimal: self({}), other({})".format(self.__decimal, other.__decimal))
        return EthAmount(self.wei + other.wei)

    def __sub__(self, other):
        if not isinstance(other, EthAmount):
            raise EthCompareTypeError(EthAmount, type(other))
        elif self.__decimal != other.__decimal:
            raise Exception("Not matches decimal: self({}), other({})".format(self.__decimal, other.__decimal))
        result = self.wei - other.wei
        if result < 0:
            raise EthNegativeValueError(result)
        return EthAmount(result)

    def __mul__(self, other):
        if isinstance(other, EthAmount):
            if self.__decimal != other.__decimal:
                raise Exception("Not matches decimal: self({}), other({})".format(self.__decimal, other.__decimal))
            amount = self.__amount * other.__amount // (10 ** self.__decimal)
        elif isinstance(other, int):
            # constant multiplication
            amount = self.__amount * other
        elif isinstance(other, float):
            other_amount = EthAmount(other)
            amount = (self * other_amount).wei
        else:
            raise EthTypeError(Union[int, EthAmount], type(other))
        return EthAmount(amount, self.__decimal)

    def __truediv__(self, other):
        if isinstance(other, EthAmount):
            if self.__decimal != other.__decimal:
                raise Exception("Not matches decimal: self({}), other({})".format(self.__decimal, other.__decimal))
            amount = self.__amount * 10 ** self.__decimal // other.__amount
        elif isinstance(other, int):
            # constant multiplication
            amount = self.__amount // other
        else:
            raise EthTypeError(Union[int, EthAmount], type(other))
        return EthAmount(amount, self.__decimal)

    def __gt__(self, other):
        if not isinstance(other, EthAmount):
            raise EthCompareTypeError(type(self), type(other))
        normal_self, normal_other = self.normalize(), other.normalize()
        return normal_self.wei > normal_other.wei

    def __lt__(self, other):
        if not isinstance(other, EthAmount):
            raise EthCompareTypeError(type(self), type(other))
        normal_self, normal_other = self.normalize(), other.normalize()
        return normal_self.wei < normal_other.wei

    def __eq__(self, other):
        if other is None:
            return False
        if not isinstance(other, EthAmount):
            raise EthCompareTypeError(type(self), type(other))
        normal_self, normal_other = self.normalize(), other.normalize()
        return normal_self.wei == normal_other.wei

    def is_zero(self) -> bool:
        return self.__amount == 0

    @classmethod
    def zero(cls):
        return cls("0x00")

    def normalize(self) -> 'EthAmount':
        # return new object with standard decimal(18)
        return self.change_decimal(18)

    def change_decimal(self, next_decimal: int) -> 'EthAmount':
        amend_exp = self.__decimal - next_decimal
        amount = self.__amount // (10 ** amend_exp) if amend_exp >= 0 else self.__amount * 10 ** abs(amend_exp)
        return EthAmount(amount, next_decimal)

    @property
    def decimal(self):
        return self.__decimal

    @property
    def wei(self) -> int:
        return self.__amount

    def bytes(self, byte_len: int = 32, byteorder: Literal["big", "little"] = "big") -> bytes:
        return self.__amount.to_bytes(byte_len, byteorder=byteorder)

    @property
    def float_str(self) -> str:
        pre_dot = str(self.__amount // 10 ** self.__decimal)
        sur_dot = str(self.__amount % 10 ** self.__decimal).zfill(self.__decimal)
        return pre_dot + "." + sur_dot

    def hex(self):
        return hex(self.__amount)

    def int(self) -> int:
        return self.__amount


def eth_amount_sum(amounts: List[EthAmount]) -> EthAmount:
    sum_amount = EthAmount("0x00")
    for amount in amounts:
        sum_amount += amount
    return sum_amount


def eth_amount_avg(amounts: List[EthAmount]) -> EthAmount:
    sum_amount = eth_amount_sum(amounts)
    return sum_amount / len(amounts)


def eth_amount_weighted_sum(amounts: List[EthAmount], weights: Union[List[float], List[EthAmount]]) -> EthAmount:
    if len(amounts) != len(weights):
        raise Exception("amounts and weight MUST have same length: {}, {}".format(len(amounts), len(weights)))

    if len(amounts) == 0:
        return EthAmount("0x00")

    weight_amounts = [EthAmount(weight) if isinstance(weight, float) else weight for weight in weights]
    total_weight = eth_amount_sum(weight_amounts)

    if total_weight == EthAmount.zero():
        return EthAmount.zero()

    weighted_sum = EthAmount("0x00")
    for i in range(len(amounts)):
        weight_rate = weight_amounts[i] / total_weight
        weighted_amount = amounts[i] * weight_rate
        weighted_sum += weighted_amount
    return weighted_sum


class BTCAmountTest(unittest.TestCase):
    def test_eth_amount_cmp(self):
        dot_one = EthAmount(0.1)
        self.assertEqual(dot_one, dot_one)
        self.assertEqual(dot_one, EthAmount("0.1"))
        self.assertEqual(dot_one, EthAmount(0.1))

        dot_two = EthAmount(0.2)
        self.assertTrue(dot_one < dot_two)
        self.assertTrue(dot_two > dot_one)

    def test_eth_amount_arithmetic(self):
        one_dot_one = EthAmount(10 ** 18 + 10 ** 17)
        one_dot_two = EthAmount(10 ** 18 + 2 * 10 ** 17)

        self.assertEqual(one_dot_one + one_dot_two, EthAmount("2.3"))
        self.assertEqual(one_dot_two - one_dot_one, EthAmount(0.1))
        self.assertEqual(one_dot_one * 10, EthAmount("11.0"))
        self.assertEqual(one_dot_one * one_dot_two, EthAmount(1.32))

    def test_eth_amount_export(self):
        one_dot_one = 10 ** 18 + 10 ** 17
        amount_obj = EthAmount(one_dot_one)

        self.assertEqual(amount_obj.hex(), hex(one_dot_one))
        self.assertEqual(amount_obj.bytes(), one_dot_one.to_bytes(32, byteorder="big"))

    def test_arithmatic_lib(self):
        amounts = [EthAmount("{}.{}".format(str(i), 0)) for i in range(10)]
        sum_amount = eth_amount_sum(amounts)
        self.assertEqual(sum_amount, EthAmount(45.0))

        avg_amount = eth_amount_avg(amounts)
        self.assertEqual(avg_amount, EthAmount(4.5))

        weights = [i / 10 for i in range(10)]
        weighted_sum = eth_amount_weighted_sum(amounts, weights)
        self.assertEqual(weighted_sum, EthAmount(6333333333333333314))
