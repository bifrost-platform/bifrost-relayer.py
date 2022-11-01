import binascii
import unittest
from string import hexdigits, digits
from sha3 import keccak_256
from typing import Union, Any
from .exceptions import EthTypeError, EthValueError

ETH_EMPTY_BYTES = b""
ETH_EMPTY_STRING = ""
ETH_HASH = keccak_256


def hex_str_to_bytes(hex_str: str) -> bytes:
    if hex_str.startswith("0x") or hex_str.startswith("0X"):
        non_prefixed_hex = hex_str[2:]
    else:
        non_prefixed_hex = hex_str

    # if the hex string is odd-length, then left-pad it to an even length
    if len(hex_str) % 2:
        padded_hex = "0" + non_prefixed_hex
    else:
        padded_hex = non_prefixed_hex

    try:
        ascii_hex = padded_hex.encode('ascii')
    except UnicodeDecodeError:
        raise ValueError(f"hex string {padded_hex} may only contain [0-9a-fA-F] characters")
    else:
        return binascii.unhexlify(ascii_hex)


def to_bytes(val: Union[bool, bytearray, bytes, int, str]) -> bytes:
    """
    Convert a hex string, integer, or bool, to a bytes representation.
    Alternatively, pass through bytes or bytearray as a bytes value.
    """
    if isinstance(val, bytes):
        return val
    elif isinstance(val, str):
        return hex_str_to_bytes(val)
    elif isinstance(val, bytearray):
        return bytes(val)
    elif isinstance(val, bool):
        return b"\x01" if val else b"\x00"
    elif isinstance(val, int):
        # Note that this int check must come after the bool check, because
        #   isinstance(True, int) is True
        if val < 0:
            raise ValueError(f"Cannot convert negative integer {val} to bytes")
        else:
            return to_bytes(hex(val))
    else:
        raise TypeError(f"Cannot convert {val!r} of type {type(val)} to bytes")


def is_hex(value: str):
    hex_digits = set(hexdigits)
    value = value.replace("0x", "")
    return all(c in hex_digits for c in value)


def is_even_hex(value: str):
    hex_digits = set(hexdigits)
    value = value.replace("0x", "")
    return all(c in hex_digits for c in value) and len(value) % 2 == 0


def is_dec(value: str):
    dec_digits = set(digits)
    value = value.replace("0x", "")
    return all(c in dec_digits for c in value)


def to_even_str_without_0x(value: str) -> str:
    if not isinstance(value, str):
        raise EthTypeError(str, type(value))
    without_0x = value[2:] if value.startswith("0x") else value
    return "0" + without_0x if len(without_0x) % 2 != 0 else without_0x


def to_even_str_with_0x(value: str) -> str:
    return "0x" + to_even_str_without_0x(value)


def to_hex_str_with_0x(val: Union[bool, bytearray, bytes, int, str]) -> str:
    if isinstance(val, bool):
        return "0x01" if val else "0x00"
    elif isinstance(val, bytearray):
        return "0x" + bytes(val).hex()
    elif isinstance(val, bytes):
        return "0x" + bytes(val).hex()
    elif isinstance(val, str):
        val = to_even_str_without_0x(val)
        return "0x" + val
    elif isinstance(val, int):
        return hex(val)
    else:
        raise TypeError(f"Cannot convert {val!r} of type {type(val)} to bytes")


def _str_float_to_wei(amount: str, decimal: int):
    # ensure input format: "1.3", "1.567"
    if not isinstance(amount, str):
        raise EthTypeError(str, type(amount))
    if amount.count(".") != 1:
        raise EthValueError(amount)
    if decimal < 0:
        raise Exception("Not allow zero decimal: {}".format(decimal))
    if decimal == 0:
        return int(float(amount))

    front, rear = amount.split(".")
    if len(rear) > decimal:
        rear = rear[:-1 * (len(rear) - decimal)]
    else:
        rear += (decimal - len(rear)) * "0"

    ret_amount = int(front, 10) * (10 ** decimal)
    ret_amount += int(rear, 10)
    return ret_amount


def _exp_notation_float_to_wei(amount: Union[float, str], decimal: int):
    if isinstance(amount, float):
        amount = str(amount)
    if "e-" not in amount:
        raise Exception("Not exponential notation float amount")

    divided = amount.split("e-")
    sig = str(float(divided[0]))
    exp = int(divided[1])
    return _str_float_to_wei(sig, decimal - exp)


def float_to_wei(amount: float, decimal: int):
    if not isinstance(amount, float):
        raise EthTypeError(float, type(amount))

    amount_str = str(amount)
    if "e-" in amount_str:
        return _exp_notation_float_to_wei(amount_str, decimal)
    elif amount_str.count(".") == 1:
        return _str_float_to_wei(amount_str, decimal)
    else:
        raise Exception("Unknown Error")


def checksum_encode(address: str) -> str:
    # encoding address to bytes
    norm_addr = address.replace("0x", "").lower()
    addr_bytes = norm_addr.encode("utf-8")
    address_hash = keccak_256(addr_bytes).hexdigest()

    checksum_address = "0x"
    for i in range(40):
        if int(address_hash[i], 16) > 7:
            checksum_address += norm_addr[i].upper()
        else:
            checksum_address += norm_addr[i]
    return checksum_address


def is_checksum_address(address: str) -> bool:
    address = address.replace('0x', '')
    addr_hash = keccak_256(address.lower()).hexdigest()
    for i in range(40):
        if int(addr_hash[i], 16) > 7 and address[i].upper() != address[i]:
            return False
        if int(addr_hash[i], 16) <= 7 and address[i].lower() != address[i]:
            return False
    return True


def recursive_tuple_to_list(p: Any):
    """ convert tuple to list recursively """
    if isinstance(p, tuple) or isinstance(p, list):
        p = list(p)
    else:
        return p
    for i, mem in enumerate(p):
        p[i] = recursive_tuple_to_list(mem)
    return p


CHAIN_ID_OFFSET = 35
V_OFFSET = 27


def to_eth_v(v_raw: int, chain_id: int = None) -> int:
    return v_raw + V_OFFSET if chain_id is None else v_raw + CHAIN_ID_OFFSET + 2 * chain_id


def to_raw_v(eth_v: int, chain_id: int = None) -> int:
    return eth_v - V_OFFSET if chain_id is None else eth_v - 2 * chain_id - CHAIN_ID_OFFSET


class TestFloatFunc(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def check_result(self, case: float, result: int):
        self.assertEqual(case, result / 10 ** 18)

    def test_str_float_cases(self):
        case1 = 2.132
        self.check_result(case1, _str_float_to_wei(str(case1), 18))

        case2 = 2.000000000011
        self.check_result(case2, _str_float_to_wei(str(case2), 18))

        case3 = 2.000000010000001
        self.check_result(case3, _str_float_to_wei(str(case3), 18))

        result = _str_float_to_wei(str(case3), 0)
        self.assertEqual(result, int(case3))
        self.assertRaises(Exception, _str_float_to_wei, (str(case3), -1))

    def test_exp_float_cases(self):
        case1 = 0.0000000001
        self.check_result(case1, _exp_notation_float_to_wei(str(case1), 18))

        case2 = 0.00000000000001
        self.check_result(case2, _exp_notation_float_to_wei(str(case2), 18))

        case3 = 0.000000000000000001
        self.check_result(case3, _exp_notation_float_to_wei(str(case3), 18))

        case4 = 0.0000000000000000001
        self.assertRaises(Exception, _exp_notation_float_to_wei, (str(case4), 18))
