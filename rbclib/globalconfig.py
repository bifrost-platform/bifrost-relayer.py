import enum
from typing import List, Dict


class RelayerRole(enum.Enum):
    GENERAL_RELAYER = 1
    SLOW_RELAYER = 2
    FAST_RELAYER = 3

    @classmethod
    def from_name(cls, role: str):
        return RelayerRole["{}_RELAYER".format(role)]


class FastRelayerConfig:
    def __init__(
        self,
        relayer_role: RelayerRole = RelayerRole.GENERAL_RELAYER,
        is_testnet: bool = False,
        slow_relayer_delay_sec: int = 0,

        rbc_event_call_delay_sec: int = 0,
        roundup_event_call_delay_sec: int = 0,

        price_oracle_assets: List[str] = None,
        price_source_url_dict: Dict[str, str] = None,
        price_source_collection_period_sec: int = 0,

        btc_hash_source_url: str = None,
        btc_hash_source_collection_period_sec: int = 0,

        validator_set_check_period_sec: int = 0,

        heart_beat_period_sec: int = 30
    ):
        if not isinstance(relayer_role, RelayerRole):
            raise Exception("In reset")
        self.relayer_role: RelayerRole = relayer_role
        self.is_testnet: bool = is_testnet
        self.slow_relayer_delay_sec: int = slow_relayer_delay_sec

        self.rbc_event_call_delay_sec: int = rbc_event_call_delay_sec
        self.roundup_event_call_delay_sec: int = roundup_event_call_delay_sec

        self.price_oracle_assets: List[str] = price_oracle_assets
        self.price_source_url_dict: Dict[str, str] = price_source_url_dict
        self.price_source_collection_period_sec: int = price_source_collection_period_sec

        self.btc_hash_source_url: str = btc_hash_source_url
        self.btc_hash_source_collection_period_sec: int = btc_hash_source_collection_period_sec

        self.validator_set_check_period_sec: int = validator_set_check_period_sec

        self.heart_beat_period_sec: int = heart_beat_period_sec

    def reset(self,
              relayer_role: RelayerRole = RelayerRole.GENERAL_RELAYER,
              is_testnet: bool = False,
              slow_relayer_delay_sec: int = 0,

              rbc_event_call_delay_sec: int = 0,
              roundup_event_call_delay_sec: int = 0,

              price_oracle_assets: List[str] = None,
              price_source_url_dict: Dict[str, str] = None,
              price_source_collection_period_sec: int = 0,

              btc_hash_source_url: str = None,
              btc_hash_source_collection_period_sec: int = 0,

              validator_set_check_period_sec: int = 0,

              heart_beat_period_sec: int = 30
              ):
        if not isinstance(relayer_role, RelayerRole):
            raise Exception("In reset")
        self.relayer_role: RelayerRole = relayer_role
        self.is_testnet: bool = is_testnet
        self.slow_relayer_delay_sec: int = slow_relayer_delay_sec

        self.rbc_event_call_delay_sec: int = rbc_event_call_delay_sec
        self.roundup_event_call_delay_sec: int = roundup_event_call_delay_sec

        self.price_oracle_assets: List[str] = price_oracle_assets
        self.price_source_url_dict: Dict[str, str] = price_source_url_dict
        self.price_source_collection_period_sec: int = price_source_collection_period_sec

        self.btc_hash_source_url: str = btc_hash_source_url
        self.btc_hash_source_collection_period_sec: int = btc_hash_source_collection_period_sec

        self.validator_set_check_period_sec: int = validator_set_check_period_sec
        self.heart_beat_period_sec: int = heart_beat_period_sec

    def is_fast_relayer(self) -> bool:
        return self.relayer_role == RelayerRole.FAST_RELAYER


relayer_config_global = FastRelayerConfig()
