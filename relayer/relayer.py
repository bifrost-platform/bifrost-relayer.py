import copy
import json
import logging
import time

from chainpy.eth.ethtype.account import EthAccount
from chainpy.eth.managers.configsanitycheck import is_meaningful, ConfigSanityChecker
from chainpy.eth.managers.utils import merge_dict
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.logger import global_logger

from rbclib.__init__ import __version__
from rbclib.utils import fetch_round_info, fetch_latest_round, find_height_by_timestamp, fetch_relayer_index
from rbclib.consts import BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, BOOTSTRAP_OFFSET_ROUNDS
from rbclib.switchable_enum import chain_primitives
from relayer.global_config import RelayerRole, relayer_config_global


class Relayer(EventBridge):
    def __init__(self, multichain_config: dict, relayer_index_cache_max_length: int = 100):
        super().__init__(multichain_config, int, relayer_index_cache_max_length)
        self.round_cache = None

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
            except ValueError:
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

    def _wait_until_node_sync(self):
        """ Wait node's block synchronization"""
        chain_manager = self.get_chain_manager_of(chain_primitives.BIFROST.name)
        while True:
            try:
                result = chain_manager.send_request("system_health", [])["isSyncing"]
            except Exception as e:
                # defensive code
                global_logger.formatted_log(
                    "WaitNodeSync",
                    address=self.active_account.address,
                    msg="error occurs \"system_health\" rpc-method: {}".format(str(e))
                )
                time.sleep(10)
                continue

            if not result:
                break

            global_logger.formatted_log(
                "WaitNodeSync",
                address=self.active_account.address,
                msg="BIFROST Node is syncing..."
            )
            time.sleep(60)

    def _register_relayer_auth(self):
        round_history_limit = min(BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, self.round_cache)
        for i in range(round_history_limit):
            relayer_index = fetch_relayer_index(self, chain_primitives.BIFROST, rnd=self.round_cache - i)
            global_logger.formatted_log(
                "UpdateAuth",
                address=self.active_account.address,
                related_chain_name=chain_primitives.BIFROST.name,
                msg="round({}):index({})".format(self.round_cache - i, relayer_index)
            )
            self.set_value_by_key(self.round_cache - i, relayer_index)

    def _determine_latest_heights_for_each_chain(self):
        current_height, _, round_length = fetch_round_info(self)
        bootstrap_start_height = max(current_height - round_length * BOOTSTRAP_OFFSET_ROUNDS, 1)

        for chain_name in self.supported_chain_list:
            chain_manager = self.get_chain_manager_of(chain_name)
            if chain_name == chain_primitives.BIFROST.name:
                chain_manager.latest_height = bootstrap_start_height
            else:
                bootstrap_start_time = self.get_chain_manager_of(chain_primitives.BIFROST.name). \
                    eth_get_block_by_height(bootstrap_start_height).timestamp
                chain_manager.latest_height = find_height_by_timestamp(chain_manager, bootstrap_start_time)

    def run_relayer(self):
        # Wait until the bifrost node completes the sync.
        self._wait_until_node_sync()

        global_logger.log(logging.INFO, "BIFROST's {}: version({}), address({})".format(
            relayer_config_global.relayer_role.name,
            __version__,
            self.active_account.address.hex()
        ))

        # store the latest round of the BIFROST network
        self.round_cache = fetch_latest_round(self, chain_primitives.BIFROST)

        # store whether this relayer is a selected relayer in each round.
        self._register_relayer_auth()

        # determine timestamp from which bootstrap starts
        self._determine_latest_heights_for_each_chain()

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
        ConfigSanityChecker(config_clone).check_config()
