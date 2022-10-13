from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import LetterCase, dataclass_json, config


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class BtcHeader:
    hash: str
    confirmations: int
    height: int
    version: int
    version_hex: str
    merkle_root: str = field(metadata=config(field_name="merkleroot"))
    time: int
    median_time: int = field(metadata=config(field_name="mediantime"))
    nonce: int
    bits: str
    difficulty: int
    chain_work: str = field(metadata=config(field_name="chainwork"))
    tx_num: int = field(metadata=config(field_name="nTx"))
    previous_hash: str = field(metadata=config(field_name="previousblockhash"))
    next_hash: Optional[str] = field(metadata=config(field_name="nextblockhash"), default_factory=str)
