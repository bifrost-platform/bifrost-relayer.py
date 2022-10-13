import json
from dataclasses import dataclass, field
from dataclasses_json import LetterCase, dataclass_json, config
from typing import List, Optional, Union, Dict

from ..ethtype.consts import ChainIndex
from ..ethtype.hexbytes import EthAddress
from ...utils import ensure_path_endswith_slash_char


def address_decoder(value: Union[str, int, bytes]) -> EthAddress:
    return EthAddress(value)


def address_encoder(value: EthAddress) -> str:
    return value.hex_without_0x()


address_meta = config(encoder=address_encoder, decoder=address_decoder)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class FeeConfig:
    type: int
    gas_price: Optional[int] = None
    max_gas_price: Optional[int] = None
    max_priority_price: Optional[int] = None
    fee_update_rates: Optional[List[float]] = None

    def __post_init__(self):
        if self.type != 0 and self.type != 2:
            raise Exception("Not supported transaction type: {}".format(self.type))
        if self.type == 0:
            if self.gas_price is None:
                raise Exception("Type0 fee config Must have gas_price")
        if self.type == 2:
            if self.max_gas_price is None or self.max_priority_price is None:
                raise Exception("Type2 fee config Must have max_gas_price and max_priority_price")

        if self.fee_update_rates is None:
            self.fee_update_rates = [1.1, 1.2, 1.3, 2]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ContractConfig:
    name: str
    address: EthAddress = field(metadata=address_meta)
    abi_path: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EventConfig:
    contract_name: str
    event_name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ChainConfig:
    chain_name: str
    block_period_sec: int
    url_with_access_key: str

    contracts: Optional[List[ContractConfig]] = None
    block_aging_period: Optional[int] = None
    transaction_commit_multiplier: Optional[int] = None
    rpc_server_downtime_allow_sec: Optional[int] = None
    bootstrap_latest_height: Optional[int] = None
    max_log_num: Optional[int] = None
    receipt_max_try: Optional[int] = None
    events: Optional[List[EventConfig]] = None
    tx_fee_type: Optional[FeeConfig] = None

    def __post_init__(self):
        if self.block_aging_period is None:
            self.block_aging_period = 0
        if self.transaction_commit_multiplier is None:
            self.transaction_commit_multiplier = 2
        if self.rpc_server_downtime_allow_sec is None:
            self.rpc_server_downtime_allow_sec = 60
        if self.bootstrap_latest_height is None:
            self.bootstrap_latest_height = 0
        if self.max_log_num is None:
            self.max_log_num = 1000
        if self.receipt_max_try is None:
            self.receipt_max_try = 10
        if self.block_aging_period is None:
            self.block_aging_period = 0

        if self.events is not None and self.contracts is not None:
            contract_names = [contract.name for contract in self.contracts]
            event_names = [event.event_name for event in self.events]
            if len(set(event_names)) != len(self.events):
                raise Exception("Duplicated Event")

            event_emitters = [event.contract_name for event in self.events]
            if not all([emitter in contract_names for emitter in event_emitters]):
                raise Exception("Some event emitted by unknown contract")


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EntityConfig:
    role: str
    account_name: str
    secret_hex: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MultiChainConfig:
    chain_monitor_period_sec: Optional[int] = None
    events: Optional[List[EventConfig]] = None

    def __post_init__(self):
        if self.chain_monitor_period_sec is None:
            self.chain_monitor_period_sec = 3


def merge_dict(base_dict: dict, add_dict: dict):
    if not isinstance(add_dict, dict):
        return add_dict

    for key, value in add_dict.items():
        if base_dict.get(key) is None:
            base_dict[key] = {}
        base_dict[key] = merge_dict(base_dict[key], add_dict[key])
    return base_dict


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class BlockHashOracle:
    name: str
    url: str
    collection_period_sec: int
    auth_id: Optional[str] = None
    auth_password: Optional[str] = None

    def __post_init__(self):
        if not self.name:
            raise Exception("Not allowed null name")
        if not self.url:
            raise Exception("Not allowed null url")
        if self.collection_period_sec == 0:
            raise Exception("Not allowed zero collection_period_sec")


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AssetPriceOracle:
    names: List[str]
    source_names: List[str]
    urls: Dict[str, str]
    collection_period_sec: int

    def __post_init__(self):
        if self.collection_period_sec == 0:
            raise Exception("Not allowed zero collection_period_sec")


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class OracleConfig:
    bitcoin_block_hash: Optional[BlockHashOracle]
    asset_prices: Optional[AssetPriceOracle]


class EntityRootConfig:
    def __init__(self,
                 chain_configs: List[ChainConfig],
                 entity_config: EntityConfig = None,
                 multichain_config: MultiChainConfig = None,
                 oracle_config: OracleConfig = None,
                 project_root_path: str = "./"):
        self.entity: EntityConfig = entity_config
        self.chains: List[ChainConfig] = chain_configs
        self.oracle_config: OracleConfig = oracle_config
        self.multichain_config: MultiChainConfig = multichain_config
        self.project_root_path = project_root_path

    @classmethod
    def from_dict(cls, config_dict: dict, private_config_dict: dict = None, project_root_path: str = "./"):
        if private_config_dict is not None:
            merged_config_dict = merge_dict(config_dict, private_config_dict)
        else:
            merged_config_dict = config_dict

        # build entity config
        if merged_config_dict.get("entity") is not None:
            entity_config = EntityConfig.from_dict(merged_config_dict["entity"])
            chain_names = merged_config_dict["entity"]["supporting_chains"]
        else:
            entity_config = None
            chain_names = list(merged_config_dict.keys())
            if "entity" in chain_names:
                chain_names.remove("entity")
            if "multichain_config" in chain_names:
                chain_names.remove("multichain_config")

        # build chain configs
        chain_configs = list()
        supported_chains = [chain_name.lower() for chain_name in chain_names]
        for chain_name in supported_chains:
            chain_config_dict = merged_config_dict[chain_name]

            # complete each path of abi file
            base_path = chain_config_dict.get("abi_base_path")
            if base_path is not None:
                base_path = ensure_path_endswith_slash_char(chain_config_dict["abi_base_path"])
            else:
                base_path = "./"

            contracts = chain_config_dict.get("contracts")
            if contracts is not None:
                for contract_dict in chain_config_dict["contracts"]:
                    contract_dict["abi_path"] = base_path + contract_dict["abi_file"]
                    del contract_dict["abi_file"]

            # build contract config list
            chain_config = ChainConfig.from_dict(merged_config_dict[chain_name])
            chain_configs.append(chain_config)

        multichain_config = merged_config_dict.get("multichain_config")
        if multichain_config is not None:
            multichain_config = MultiChainConfig.from_dict(multichain_config)

        oracle_config = merged_config_dict.get("oracle_config")
        if oracle_config is not None:
            oracle_config = OracleConfig.from_dict(oracle_config)

        project_root_path = ensure_path_endswith_slash_char(project_root_path)
        return cls(chain_configs, entity_config, multichain_config, oracle_config, project_root_path)

    @classmethod
    def from_config_files(cls, config_file_path: str, private_config_file_path: str = None, project_root: str = "./"):
        project_root = ensure_path_endswith_slash_char(project_root)

        config_file_path = project_root + config_file_path
        with open(config_file_path, "r") as f:
            public_config = json.load(f)

        private_config_file_path = project_root + private_config_file_path
        if private_config_file_path is not None:
            with open(private_config_file_path, "r") as f:
                private_config = json.load(f)
        return cls.from_dict(public_config, private_config, project_root)

    def supported_chains(self) -> List[ChainIndex]:
        return [eval("ChainIndex." + chain_config.chain_name.upper()) for chain_config in self.chains]

    def get_chain_config(self, chain_index: ChainIndex):
        for chain_config in self.chains:
            if chain_config.chain_name.upper() == chain_index.name:
                return chain_config
        return None
