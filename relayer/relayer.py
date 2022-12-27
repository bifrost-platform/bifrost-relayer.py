import json
from chainpy.eth.ethtype.account import EthAccount
from chainpy.eth.managers.utils import merge_dict
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.eth.ethtype.consts import ChainIndex
from chainpy.eventbridge.multichainmonitor import bootstrap_logger

from rbclib.bifrostutils import fetch_sorted_previous_relayer_list, fetch_round_info, \
    fetch_latest_round, find_height_by_timestamp
from rbclib.consts import BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, BOOTSTRAP_OFFSET_ROUNDS
from rbclib.periodicevents import BtcHashUpOracle, AuthDownOracle, PriceUpOracle
import time

from .__init__ import __version__


class Relayer(EventBridge):
    def __init__(self, multichain_config: dict, relayer_index_cache_max_length: int = 100):
        super().__init__(multichain_config, int, relayer_index_cache_max_length)
        self.current_rnd = None

    @classmethod
    def init_from_config_files(cls, relayer_config_path: str, private_config_path: str = None, private_key: str = None):
        with open(relayer_config_path, "r") as f:
            relayer_config_dict = json.load(f)

        private_config_dict = None
        if private_config_path is not None:
            with open(private_config_path, "r") as f:
                private_config_dict = json.load(f)

        return cls.init_from_dicts(
            relayer_config_dict,
            private_config_dict=private_config_dict,
            private_key=private_key
        )

    @classmethod
    def init_from_dicts(cls, relayer_config_dict: dict, private_config_dict: dict = None, private_key: str = None):
        merged_dict = merge_dict(relayer_config_dict, private_config_dict)
        if private_key is not None:
            merged_dict["entity"]["secret_hex"] = hex(EthAccount.from_secret(private_key).priv)

        oracle_config = merged_dict.get("oracle_config")
        Relayer.init_classes(oracle_config)
        return cls(merged_dict)

    @staticmethod
    def init_classes(oracle_config_dict: dict):
        # setup hardcoded value (not from config file) because it's a system parameter
        AuthDownOracle.setup(60)

        price_oracle_config = oracle_config_dict["asset_prices"]
        PriceUpOracle.setup(
            price_oracle_config["names"],
            price_oracle_config["source_names"],
            price_oracle_config["urls"],
            price_oracle_config["collection_period_sec"]
        )

        btc_hash_oracle_config = oracle_config_dict["bitcoin_block_hash"]
        BtcHashUpOracle.setup(
            btc_hash_oracle_config["url"],
            btc_hash_oracle_config["collection_period_sec"]
        )

    def _register_relayer_index(self, rnd: int):
        sorted_validator_list = fetch_sorted_previous_relayer_list(self, ChainIndex.BIFROST, rnd)
        relayer_lower_list = [relayer_addr.lower() for relayer_addr in sorted_validator_list]
        sorted_relayer_list = sorted(relayer_lower_list)

        try:
            my_addr = self.active_account.address.hex().lower()
            relayer_index = sorted_relayer_list.index(my_addr)
            self.set_value_by_key(rnd, relayer_index)
        except ValueError:
            pass

    def wait_until_node_sync(self):
        while True:
            # wait node's block synchronization
            chain_manager = self.get_chain_manager_of(ChainIndex.BIFROST)
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

        # check whether this relayer belongs to current validator list
        self.current_rnd = fetch_latest_round(self, ChainIndex.BIFROST)
        round_history_limit = min(BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, self.current_rnd)
        for i in range(round_history_limit):
            self._register_relayer_index(self.current_rnd - i)

        # determine timestamp which bootstrap starts from
        current_height, _, round_length = fetch_round_info(self)
        bootstrap_start_height = max(current_height - round_length * BOOTSTRAP_OFFSET_ROUNDS, 1)
        bootstrap_start_time = self.get_chain_manager_of(ChainIndex.BIFROST).\
            eth_get_block_by_height(bootstrap_start_height).timestamp

        # determine heights of each chain which bootstrap starts from
        for chain_index in self.supported_chain_list:
            chain_manager = self.get_chain_manager_of(chain_index)
            if chain_index == ChainIndex.BIFROST:
                chain_manager.latest_height = bootstrap_start_height
            else:
                chain_manager.latest_height = find_height_by_timestamp(chain_manager, bootstrap_start_time)

        bootstrap_logger.info("BIFROST's Relayer: {}".format(__version__))
        bootstrap_logger.info("Relayer-has-been-launched ({})".format(self.active_account.address.hex()))

        # run relayer
        self.run_eventbridge()
