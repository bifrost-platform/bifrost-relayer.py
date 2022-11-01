from typing import Union

from dataclasses_json import config

from relayer.chainpy.eth.ethtype.exceptions import EthNotHex
from relayer.chainpy.eth.ethtype.hexbytes import EthHexBytes, EthHashBytes, EthAddress
from relayer.chainpy.eth.ethtype.utils import is_hex

"""
{TYPE}Meta - store value as a specific "TYPE"
- decoder: importing function
- encoder: exporting function
"""


def hex_to_int(value: Union[str, int]) -> int:
    if isinstance(value, int):
        return value
    if is_hex(value):
        ret = int(value, 16)
        return ret
        # return int(value, 16)
    raise EthNotHex(type(value))


IntegerMeta = config(
    decoder=lambda value: hex_to_int(value) if value is not None and value != "" else None,
    encoder=lambda value: hex(value) if value is not None else None
)

EthHexBytesMeta = config(
    decoder=lambda value: EthHexBytes(value),
    encoder=lambda value: value.hex() if value is not None else None
)

EthHexBytesListMeta = config(
    decoder=lambda values: [EthHexBytes(value) for value in values],
    encoder=lambda values: [value.hex() for value in values]
)

EthHashBytesMeta = config(
    decoder=lambda value: EthHashBytes(value),
    encoder=lambda value: value.hex() if value is not None else None
)

EthHashBytesListMeta = config(
    decoder=lambda values: [EthHashBytes(value) for value in values],
    encoder=lambda values: [value.hex() for value in values]
)

EthAddrMeta = config(
    decoder=lambda value: EthAddress(value),
    encoder=lambda value: value.hex() if value is not None else None
)

EthAddrListMeta = config(
    decoder=lambda values: [EthAddress(value) for value in values],
    encoder=lambda values: [value.hex() for value in values]
)
