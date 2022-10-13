from typing import Union

from ..ethtype.chaindata import EthLog
from ..ethtype.consts import ChainIndex
from ..ethtype.hexbytes import EthAddress, EthHashBytes, EthHexBytes


class DetectedEvent:
    def __init__(self, chain_index: ChainIndex, contract_name: str, event_name: str, log: EthLog):
        self.chain_index = chain_index
        self.contract_name = contract_name
        self.event_name = event_name
        self.log = log

    def __repr__(self):
        return "{}({}_on_{}:{})".format(
            self.__class__.__name__,
            self.event_name,
            self.chain_index.name,
            self.log.data.hex()
        )

    @classmethod
    def from_dict(cls, detected_event_dict: dict):
        chain_index = eval("ChainIndex." + detected_event_dict["chain_name"].upper())
        log_obj = EthLog.from_dict(detected_event_dict["log"])
        return cls(chain_index, detected_event_dict["contract_name"], detected_event_dict["event_name"], log_obj)

    def to_dict(self) -> dict:
        return {
            "chain_name": self.chain_index.name,
            "contract_name": self.contract_name,
            "event_name": self.event_name,
            "log": self.log.to_dict()
        }

    @property
    def contract_address(self) -> EthAddress:
        return self.log.address

    @property
    def topic(self) -> EthHashBytes:
        topic = self.log.topics[0]
        if not isinstance(topic, EthHashBytes):
            topic = EthHashBytes(topic)
        return topic

    @property
    def transaction_hash(self) -> EthHashBytes:
        tx_hash = self.log.transaction_hash
        if not isinstance(tx_hash, EthHashBytes):
            tx_hash = EthHashBytes(tx_hash)
        return tx_hash

    @property
    def transaction_index(self) -> int:
        return self.log.transaction_index

    @property
    def block_hash(self) -> EthHashBytes:
        block_hash = self.block_hash
        if not isinstance(block_hash, EthHashBytes):
            block_hash = EthHashBytes(block_hash)
        return block_hash

    @property
    def block_number(self) -> int:
        return self.log.block_number

    @property
    def log_index(self) -> int:
        return self.log.log_index

    @property
    def data(self) -> EthHexBytes:
        return self.log.data

    @data.setter
    def data(self, data: Union[bool, bytearray, bytes, int, str, EthHexBytes]):
        self.log.data = data if isinstance(data, EthHexBytes) else EthHexBytes(data)

    @property
    def removed(self) -> bool:
        return self.log.removed
