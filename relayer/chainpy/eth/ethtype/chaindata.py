from dataclasses import dataclass, field

from dataclasses_json import dataclass_json, LetterCase, config, Exclude
from typing import Union, Optional, List, Dict

from .dataclassmeta import IntegerMeta, EthHexBytesMeta, EthHashBytesMeta, EthAddrMeta, EthHashBytesListMeta
from .exceptions import *
from .hexbytes import EthHashBytes, EthAddress, EthHexBytes
from .utils import is_hex


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EthTransaction:
    hash: EthHashBytes = field(metadata=EthHashBytesMeta)

    block_hash: Optional[EthHashBytes] = field(metadata=EthHashBytesMeta, default_factory=str)
    block_number: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    sender: Optional[EthAddress] = field(
        metadata=config(
            field_name="from",
            encoder=lambda value: value.hex(),
            decoder=lambda value: EthAddress(value)
        ),
        default_factory=str
    )
    gas: int = field(metadata=IntegerMeta, default_factory=int)
    gas_price: int = field(metadata=IntegerMeta, default_factory=int)

    input: EthHexBytes = field(metadata=EthHexBytesMeta, default_factory=str)
    nonce: int = field(metadata=IntegerMeta, default_factory=int)
    r: int = field(metadata=IntegerMeta, default_factory=int)
    s: int = field(metadata=IntegerMeta, default_factory=int)
    v: int = field(metadata=IntegerMeta, default_factory=int)
    transaction_index: int = field(metadata=IntegerMeta, default_factory=int)
    value: int = field(metadata=IntegerMeta, default_factory=int)

    # optional depends on rpc versions
    type: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    to: Optional[EthAddress] = field(metadata=EthAddrMeta, default_factory=str)

    # type 2 only
    access_list: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    max_fee_per_gas: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    max_priority_fee_per_gas: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    chain_id: Optional[int] = field(metadata=IntegerMeta, default_factory=int)

    def __post_init__(self):
        if self.block_hash == EthHashBytes.zero():
            self.type = -1
        elif self.access_list is None:
            self.type = 0
        else:
            self.type = 2


def encode_transaction(tx: EthTransaction):
    if tx.type == -1:
        return tx.hash.hex()
    else:
        return tx.to_dict()


def decode_transaction(tx: Union[dict, str]):
    if isinstance(tx, str) and is_hex(tx):
        return EthTransaction.from_dict({"hash": tx})
    elif isinstance(tx, dict):
        return EthTransaction.from_dict(tx)
    else:
        raise EthTypeError(Optional[dict, str], type(tx))


EthTransactionListMeta = config(
    decoder=lambda values: [decode_transaction(value) for value in values],
    encoder=lambda values: [encode_transaction(value) for value in values]
)


def check_verbosity(values: list):
    if len(values) == 0:
        return False

    criteria = values[0]
    if isinstance(criteria, EthTransaction):
        return criteria.block_hash != EthHashBytes.zero()
    else:
        if isinstance(criteria, dict):
            return True
        elif isinstance(criteria, str) and is_hex(criteria):
            return False
        else:
            raise EthTypeError(Optional[dict, str], type(criteria))


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EthBlock:
    verbose: bool = field(init=False, metadata=config(exclude=Exclude.ALWAYS))
    type: int = field(init=False, metadata=config(exclude=Exclude.ALWAYS))

    difficulty: int = field(metadata=IntegerMeta)
    extra_data: EthHexBytes = field(metadata=EthHexBytesMeta)
    gas_limit: int = field(metadata=IntegerMeta)
    gas_used: int = field(metadata=IntegerMeta)
    hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    logs_bloom: EthHexBytes = field(metadata=EthHexBytesMeta)
    miner: EthAddress = field(metadata=EthAddrMeta)

    number: int = field(metadata=IntegerMeta)
    parent_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    receipts_root: EthHashBytes = field(metadata=EthHashBytesMeta)
    sha3_uncles: EthHashBytes = field(metadata=EthHashBytesMeta)
    size: int = field(metadata=IntegerMeta)
    state_root: EthHashBytes = field(metadata=EthHashBytesMeta)
    timestamp: int = field(metadata=IntegerMeta)
    total_difficulty: int = field(metadata=IntegerMeta)
    transactions_root: EthHashBytes = field(metadata=EthHashBytesMeta)
    transactions: List[EthTransaction] = field(metadata=EthTransactionListMeta)
    uncles: List[EthHashBytes] = field(metadata=EthHashBytesListMeta)

    # required except to bifrost network
    mix_hash: EthHashBytes = field(metadata=EthHashBytesMeta, default_factory=str)
    nonce: int = field(metadata=IntegerMeta, default_factory=int)

    # BaseFee was added by EIP - 1559 and is ignored in legacy headers.
    base_fee_per_gas: Optional[int] = field(metadata=IntegerMeta, default_factory=str)

    def __post_init__(self):
        self.verbose = check_verbosity(self.transactions)
        self.type = 0 if self.base_fee_per_gas is None else 2


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EthLog:
    # log has single type
    address: EthAddress = field(metadata=EthAddrMeta)
    block_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    block_number: int = field(metadata=IntegerMeta)
    data: EthHexBytes = field(metadata=EthHexBytesMeta)
    log_index: int = field(metadata=IntegerMeta)
    removed: bool
    topics: list = field(metadata=EthHashBytesListMeta)
    transaction_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    transaction_index: int = field(metadata=IntegerMeta)


EthLogListMeta = config(
    decoder=lambda values: [EthLog.from_dict(value) for value in values],
    encoder=lambda values: [value.to_dict() for value in values]
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EthReceipt:
    # receipt has single type
    block_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    block_number: int = field(metadata=IntegerMeta)

    cumulative_gas_used: int = field(metadata=IntegerMeta)
    effective_gas_price: int = field(metadata=IntegerMeta)
    sender: EthAddress = field(
        metadata=config(
            field_name="from",
            encoder=lambda value: value.hex(),
            decoder=lambda value: EthAddress(value)
        )
    )
    gas_used: int = field(metadata=IntegerMeta)
    logs: List[EthLog] = field(metadata=EthLogListMeta)
    logs_bloom: EthHexBytes = field(metadata=EthHexBytesMeta)
    status: int = field(metadata=IntegerMeta)
    to: EthAddress = field(metadata=EthAddrMeta)
    transaction_hash: EthHashBytes = field(metadata=EthHashBytesMeta)
    transaction_index: int = field(metadata=IntegerMeta)

    type: Optional[int] = field(metadata=IntegerMeta, default_factory=int)
    contract_address: Optional[EthAddress] = field(metadata=EthAddrMeta, default_factory=str)

    def __post_init__(self):
        if self.type is None:
            self.type = 0
