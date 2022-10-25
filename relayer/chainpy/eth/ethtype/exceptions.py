from typing import Any


class EthTooLowPriority(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class EthFeeCapError(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class EthUnderPriced(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class EthNotHex(Exception):
    def __init__(self, actual_type: type):
        msg = "Expected type: hex, but actual {}".format(actual_type)
        super().__init__(msg)


class EthNotExpectedNone(Exception):
    def __init__(self, expected_type: type):
        msg = "Expected type: {}, but None".format(expected_type)
        super().__init__(msg)


class EthExpectedNone(Exception):
    def __init__(self, actual_type: type):
        msg = "Expected None, but actual {}".format(actual_type)
        super().__init__(msg)


class EthTypeError(Exception):
    def __init__(self, expected_type: type, actual_type: type):
        msg = "Expected type: {}, but actual {}".format(expected_type, actual_type)
        super().__init__(msg)


class EthValueError(Exception):
    def __init__(self, value: Any):
        msg = "Invalid value: {}".format(value)
        super().__init__(msg)


class EthValueLengthError(Exception):
    def __init__(self, value_len: int):
        msg = "Not allowed length of the value: {}".format(value_len)
        super().__init__(msg)


class EthCompareTypeError(Exception):
    def __init__(self, type1: type, type2: type):
        msg = "{} can not be compared with {}".format(type1, type2)
        super().__init__(msg)


class EthOutOfRangeError(Exception):
    def __init__(self, index: int, maximum: int):
        msg = "The index({}) is out of range({})".format(index, maximum)
        super().__init__(msg)


class EthNegativeValueError(Exception):
    def __init__(self, value: int):
        msg = "Not allowed negative value: {}".format(value)
        super().__init__(msg)


class EthUnknownSpecError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class EthAlreadyExistError(Exception):
    def __init__(self, key: str = None, value = None):
        msg = "The key({}) or the value({}) already exists".format(key, value)
        super().__init__(msg)


class EthNotExistError(Exception):
    def __init__(self, key: str):
        msg = "The value related to key({})) does not exists".format(key)
        super().__init__(msg)


class EthIntOverflowError(Exception):
    def __init__(self, value: int):
        msg = "Overflow occurs: {}".format(value)
        super().__init__(msg)


class EthNotSupportedOptionError(Exception):
    def __init__(self, opt_name: str):
        msg = "Not supported option: {}".format(opt_name)
        super().__init__(msg)


class EthStatusNotMatchError(Exception):
    def __init__(self, expected_status: Any, actual_status: Any):
        msg = "Expected status: {}, but {}".format(expected_status, actual_status)
        super().__init__(msg)


class EthTxMemberNotCompleteError(Exception):
    def __init__(self, member_name: str, value: Any):
        msg = "Invalid {}: {}".format(member_name, value)
        super().__init__(msg)


class EthNoAccountError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class RpcExceedRequestTime(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
