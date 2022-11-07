from typing import cast
from .utils import *


ETH_HASH_BYTES_SIZE = 32
ETH_ADDR_BYTES_SIZE = 20


class EthHexBytes(bytes):
    """
    Hex byte Class with Ensured Size.
    """
    def __new__(cls, val: Union[bool, bytearray, bytes, int, str], size: int = None) -> Union['EthHexBytes', None]:
        if val is None:
            return val

        data = to_bytes(val)
        expected_size = size if size is not None else len(data)

        if len(data) > expected_size:
            raise Exception(size)
        if len(data) < expected_size:
            data = b"\00" * (expected_size - len(data)) + data

        return cast(EthHexBytes, super().__new__(cls, data))

    def __repr__(self) -> str:
        class_name = str(type(self)).split(".")[-1].replace("'", "").replace(">", "")
        return "{}({})".format(class_name, "0x" + bytes(self).hex())

    def __eq__(self, other):
        if isinstance(other, EthHexBytes):
            return bytes(self) == bytes(other)
        elif isinstance(other, int):
            other_obj = EthHexBytes(other)
            return self.int() == other_obj.int()
        else:
            other_obj = EthHexBytes(other)
            return bytes(self) == bytes(other_obj)

    def __add__(self, other) -> 'EthHexBytes':
        if isinstance(other, EthHexBytes):
            return EthHexBytes(bytes(self) + bytes(other), len(self) + len(other))
        elif isinstance(other, bytes):
            return EthHexBytes(bytes(self) + other, len(self) + len(other))
        else:
            raise EthTypeError(Union[EthHexBytes, bytes], type(other))

    def __getitem__(self, index: int) -> 'EthHexBytes':
        result = super().__getitem__(index)
        return type(self)(result)

    def __len__(self) -> int:
        return len(bytes(self))

    def hex(self, **kwargs) -> str:
        return "0x" + super().hex()

    def hex_without_0x(self) -> str:
        return super().hex()

    def int(self) -> int:
        return int.from_bytes(self, byteorder="big")

    def bytes(self) -> bytes:
        return bytes(self)

    @staticmethod
    def zero():
        return EthHexBytes("0x00", 32)


class EthHashBytes(EthHexBytes):
    def __new__(cls, val: Union[bool, bytearray, bytes, int, str]) -> Union['EthHashBytes', None]:
        obj = super().__new__(cls, val, ETH_HASH_BYTES_SIZE)
        return cast(EthHashBytes, obj)


class EthAddress(EthHexBytes):
    """
    Hex String Class with Ensured Size.
    """
    def __new__(cls, val: Union[bool, bytearray, bytes, int, str]) -> Union['EthAddress', None]:
        return cast(EthAddress, super().__new__(cls, val, ETH_ADDR_BYTES_SIZE))

    def with_checksum(self):
        return checksum_encode(self.hex())

    @staticmethod
    def zero():
        return EthAddress("0x0000000000000000000000000000000000000000")


class EthHexBytesTest(unittest.TestCase):
    def check_basic(self, data: EthHexBytes, expected_hex: str):
        expected_bytes = bytes.fromhex(expected_hex[2:])
        # check equality
        self.assertEqual(data, expected_hex)
        self.assertEqual(data, expected_bytes)
        self.assertEqual(data, int(expected_hex, 16))

        # check exporting function
        self.assertEqual(data.hex(), expected_hex)
        self.assertEqual(data.int(), int(expected_hex, 16))
        self.assertEqual(data.bytes(), expected_bytes)

    def test_eth_hex_bytes(self):
        data_obj = EthHexBytes("0x001234567890")
        # check initiation
        self.assertEqual(type(data_obj), EthHexBytes)
        self.check_basic(data_obj, "0x001234567890")

        # check addition
        add_data_obj = data_obj + data_obj
        self.assertEqual(type(add_data_obj), EthHexBytes)
        self.check_basic(add_data_obj, "0x001234567890001234567890")

        # check slicing function
        sliced = data_obj[2:]
        self.assertEqual(type(sliced), EthHexBytes)
        self.check_basic(sliced, "0x34567890")

    def test_eth_sized_hex_string(self):
        data = EthHexBytes("0x001234567890", 6)
        self.assertEqual(data, "0x001234567890")

        # over-sized test
        over_sized = EthHexBytes("0x001234567890", 7)
        self.assertEqual(len(over_sized), 7)

        # under-sized test
        self.assertRaises(Exception, EthHexBytes, ("0x001234567890", 5))

    def test_eth_hash(self):
        data = EthHashBytes("0x0012345678900012345678900012345678900012345678900012345678900012")
        self.assertEqual(data, "0x0012345678900012345678900012345678900012345678900012345678900012")
        self.assertEqual(len(data), ETH_HASH_BYTES_SIZE)
        self.assertRaises(Exception, data == "0x12345678900012345678900012345678900012345678900012345678900012")

    def test_eth_address(self):
        data = EthAddress("0x466D25b791FD4882e15aF01FC28a633014104B2b".lower())  # without checksum
        self.assertEqual(data, "0x466D25b791FD4882e15aF01FC28a633014104B2b")
        self.assertRaises(Exception, data.hex() == "0x466D25b791FD4882e15aF01FC28a633014104B2b")
        self.assertEqual(data.with_checksum(), "0x466D25b791FD4882e15aF01FC28a633014104B2b")
