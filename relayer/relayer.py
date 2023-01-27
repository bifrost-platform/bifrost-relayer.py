import copy
import json
import time
import logging

from chainpy.eth.ethtype.account import EthAccount
from chainpy.eth.managers.utils import merge_dict
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eth.managers.configsanitycheck import ConfigChecker
from chainpy.eth.managers.configsanitycheck import is_meaningful
from chainpy.logger import Logger

from rbclib.bifrostutils import fetch_sorted_previous_relayer_list, fetch_round_info, \
    fetch_latest_round, find_height_by_timestamp
from rbclib.consts import BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, BOOTSTRAP_OFFSET_ROUNDS
from rbclib.globalconfig import RelayerRole, relayer_config_global
from rbclib.switchable_enum import SwitchableChain

from .__init__ import __version__


class Relayer(EventBridge):
    def __init__(self, multichain_config: dict, relayer_index_cache_max_length: int = 100):
        super().__init__(multichain_config, int, relayer_index_cache_max_length)
        self.current_rnd = None

    @classmethod
    def init_from_config_files(
            cls,
            relayer_config_path: str,
            private_config_path: str = None,
            private_key: str = None,
            role: RelayerRole = None,
            slow_relayer_delay_sec: int = None
    ):
        with open(relayer_config_path, "r") as f:
            relayer_config_dict = json.load(f)

        private_config_dict = None
        if private_config_path is not None:
            with open(private_config_path, "r") as f:
                private_config_dict = json.load(f)

        return cls.init_from_dicts(
            relayer_config_dict,
            private_config_dict=private_config_dict,
            private_key=private_key,
            role=role,
            slow_relayer_delay_sec=slow_relayer_delay_sec
        )

    @classmethod
    def init_from_dicts(
            cls,
            relayer_config_dict: dict,
            private_config_dict: dict = None,
            private_key: str = None,
            role: RelayerRole = None,
            slow_relayer_delay_sec: int = None,
            is_testnet: bool = False
    ):
        merged_dict = merge_dict(relayer_config_dict, private_config_dict)
        if private_key is not None:
            merged_dict["entity"]["secret_hex"] = hex(EthAccount.from_secret(private_key).priv)

        # check a correctness of the relayer config
        Relayer.config_sanity_check(merged_dict)

        # forced change relayer's role
        if role is None:
            role = RelayerRole[merged_dict["entity"]["role"].replace("-", "_").capitalize()]

        if role == RelayerRole.SLOW_RELAYER and slow_relayer_delay_sec is None:
            try:
                slow_relayer_delay_sec = merged_dict["entity"]["slow_relayer_delay_sec"]
            except ValueError as e:
                raise Exception("Slow relayer, but no delay in config file")

        # check whether oracle relayer or not
        oracle_config = merged_dict.get("oracle_config")
        is_price_oracle_relayer = oracle_config is not None and is_meaningful(oracle_config["asset_prices"])
        is_btc_oracle_relayer = oracle_config is not None and is_meaningful(oracle_config["bitcoin_block_hash"])

        relayer_config_global.reset(
            relayer_role=role,
            is_testnet=is_testnet,
            slow_relayer_delay_sec=slow_relayer_delay_sec,
            rbc_event_call_delay_sec=600,
            roundup_event_call_delay_sec=200,
            price_oracle_assets=oracle_config["asset_prices"]["names"] if is_price_oracle_relayer else None,
            price_source_url_dict=oracle_config["asset_prices"]["urls"] if is_price_oracle_relayer else None,
            price_source_collection_period_sec=300,
            btc_hash_source_url=oracle_config["bitcoin_block_hash"]["url"] if is_btc_oracle_relayer else None,
            btc_hash_source_collection_period_sec=300,
            validator_set_check_period_sec=60
        )

        return cls(merged_dict)

    def _register_relayer_index(self, rnd: int):
        sorted_validator_list = fetch_sorted_previous_relayer_list(self, SwitchableChain.BIFROST, rnd)
        relayer_lower_list = [relayer_addr.lower() for relayer_addr in sorted_validator_list]
        sorted_relayer_list = sorted(relayer_lower_list)

        try:
            my_addr = self.active_account.address.hex().lower()
            relayer_index = sorted_relayer_list.index(my_addr)
            print("RegisterMyIndex: round({}), index({})".format(rnd, relayer_index))
            self.set_value_by_key(rnd, relayer_index)
        except ValueError:
            pass

    def wait_until_node_sync(self):
        while True:
            # wait node's block synchronization
            chain_manager = self.get_chain_manager_of(SwitchableChain.BIFROST)
            try:
                result = chain_manager.send_request("system_health", [])["isSyncing"]
            except Exception as e:
                time.sleep(10)
                continue

            if not result:
                break
            else:
                print(">>> BIFROST Node is syncing..")
                time.sleep(60)

    def run_relayer(self):
        # Wait until the bifrost node completes the sync.
        self.wait_until_node_sync()

        # store whether this relayer is a selected validator in each round.
        self.current_rnd = fetch_latest_round(self, SwitchableChain.BIFROST)
        round_history_limit = min(BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, self.current_rnd)
        for i in range(round_history_limit):
            self._register_relayer_index(self.current_rnd - i)

        # determine timestamp which bootstrap starts from
        current_height, _, round_length = fetch_round_info(self)
        bootstrap_start_height = max(current_height - round_length * BOOTSTRAP_OFFSET_ROUNDS, 1)

        # determine heights of each chain which bootstrap starts from
        for chain_index in self.supported_chain_list:
            chain_manager = self.get_chain_manager_of(chain_index)
            if chain_index == SwitchableChain.BIFROST:
                chain_manager.latest_height = bootstrap_start_height
            else:
                bootstrap_start_time = self.get_chain_manager_of(SwitchableChain.BIFROST). \
                    eth_get_block_by_height(bootstrap_start_height).timestamp
                chain_manager.latest_height = find_height_by_timestamp(chain_manager, bootstrap_start_time)

        logger = Logger("Bootstrap", logging.INFO)
        logger.info("BIFROST's {}: version({}), address({})".format(
            relayer_config_global.relayer_role.name,
            __version__,
            self.active_account.address.hex())
        )

        # run relayer
        self.run_eventbridge()

    @staticmethod
    def config_sanity_check_from_files(public_config_path: str, private_config_path: str = None):
        with open(public_config_path, "r") as f:
            public_config = json.load(f)

        private_config = None
        if private_config_path is not None:
            with open(private_config_path, "r") as f:
                private_config = json.load(f)

        Relayer.config_sanity_check(merge_dict(public_config, private_config))

    @staticmethod
    def config_sanity_check(config: dict):
        config_clone = copy.deepcopy(config)
        ConfigChecker.check_config(config_clone)
