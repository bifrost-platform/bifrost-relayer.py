from dataclasses import dataclass, field

from dataclasses_json import dataclass_json, LetterCase, config, Exclude
from typing import Optional, List

from .dataclassmeta import IntegerMeta, EthHexBytesMeta, EthHashBytesMeta, EthAddrMeta, EthHashBytesListMeta
from .hexbytes import EthHashBytes, EthAddress, EthHexBytes
from .transaction import EthTransaction, EthTransactionListMeta, check_transaction_verbosity


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
        self.verbose = check_transaction_verbosity(self.transactions)
        self.type = 0 if self.base_fee_per_gas is None else 2

    def serialize(self) -> EthHexBytes:
        # TODO impl.
        raise Exception("Not implemented yet")

    def block_hash(self) -> EthHashBytes:
        # TODO impl.
        raise Exception("Not implemented yet")


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
