import copy
import json
from typing import Optional
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
from rbclib.chainevents import RbcEvent, RoundUpEvent
from rbclib.consts import BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, BOOTSTRAP_OFFSET_ROUNDS
from rbclib.periodicevents import BtcHashUpOracle, VSPFeed, PriceUpOracle
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
            role: str = None,
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
            role: str = None,
            slow_relayer_delay_sec: int = None
    ):
        merged_dict = merge_dict(relayer_config_dict, private_config_dict)
        if private_key is not None:
            merged_dict["entity"]["secret_hex"] = hex(EthAccount.from_secret(private_key).priv)

        # forced change relayer's role
        if is_meaningful(role) and role.capitalize() == "Slow-relayer":
            merged_dict["entity"]["role"] = role.capitalize()
            merged_dict["entity"]["slow_relayer_delay_sec"] = slow_relayer_delay_sec

        # check a correctness of the relayer config
        Relayer.config_sanity_check(merged_dict)

        # check whether oracle relayer or not
        oracle_config = merged_dict.get("oracle_config")

        is_price_oracle_relayer = oracle_config is not None and is_meaningful(oracle_config["asset_prices"])
        price_oracle_config = oracle_config["asset_prices"] if is_price_oracle_relayer else None

        is_btc_oracle_relayer = oracle_config is not None and is_meaningful(oracle_config["bitcoin_block_hash"])
        btc_oracle_config = oracle_config["bitcoin_block_hash"] if is_btc_oracle_relayer else None

        slow_relayer_delay_sec = None
        if merged_dict["entity"]["role"].capitalize() == "Slow-relayer":
            slow_relayer_delay_sec = merged_dict["entity"]["slow_relayer_delay_sec"]

        Relayer.init_classes(
            slow_relayer_delay_sec=slow_relayer_delay_sec,
            price_oracle_config=price_oracle_config,
            btc_hash_oracle_config=btc_oracle_config
        )

        return cls(merged_dict)

    @staticmethod
    def init_classes(
            slow_relayer_delay_sec: Optional[int] = 60,
            auth_down_oracle_period_sec: int = 60,
            price_oracle_config: Optional[dict] = None,
            btc_hash_oracle_config: Optional[dict] = None,
    ):
        # setup hardcoded value (not from config file) because it's a system parameter
        VSPFeed.setup(auth_down_oracle_period_sec)

        if slow_relayer_delay_sec is not None:
            RbcEvent.AGGREGATED_DELAY_SEC = slow_relayer_delay_sec
            RoundUpEvent.AGGREGATED_DELAY_SEC = slow_relayer_delay_sec

        PriceUpOracle.setup(
            price_oracle_config["names"],
            price_oracle_config["urls"],
            price_oracle_config["collection_period_sec"]
        )

        BtcHashUpOracle.setup(
            btc_hash_oracle_config["url"],
            btc_hash_oracle_config["collection_period_sec"]
        )

    @staticmethod
    def set_relayer_role(role):
        role = role.capitalize()

        if role == "User" or role == "Relayer":
            RbcEvent.FAST_RELAYER = False
            RoundUpEvent.FAST_RELAYER = False
            RbcEvent.AGGREGATED_DELAY_SEC = 0
            RoundUpEvent.AGGREGATED_DELAY_SEC = 0

        elif role == "Fast-relayer":
            RbcEvent.FAST_RELAYER = True
            RoundUpEvent.FAST_RELAYER = True
            RbcEvent.AGGREGATED_DELAY_SEC = 0
            RoundUpEvent.AGGREGATED_DELAY_SEC = 0

        elif role == "Slow-relayer":
            RbcEvent.FAST_RELAYER = False
            RoundUpEvent.FAST_RELAYER = False
            if RbcEvent.AGGREGATED_DELAY_SEC == 0 or RoundUpEvent.AGGREGATED_DELAY_SEC == 0:
                raise Exception("Slow relayer has no delay")

    def _register_relayer_index(self, rnd: int):
        sorted_validator_list = fetch_sorted_previous_relayer_list(self, SwitchableChain.BIFROST, rnd)
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

        # check whether this relayer belongs to current validator list
        self.current_rnd = fetch_latest_round(self, SwitchableChain.BIFROST)
        round_history_limit = min(BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS, self.current_rnd)
        for i in range(round_history_limit):
            self._register_relayer_index(self.current_rnd - i)

        # determine timestamp which bootstrap starts from
        current_height, _, round_length = fetch_round_info(self)
        bootstrap_start_height = max(current_height - round_length * BOOTSTRAP_OFFSET_ROUNDS, 1)
        bootstrap_start_time = self.get_chain_manager_of(SwitchableChain.BIFROST).\
            eth_get_block_by_height(bootstrap_start_height).timestamp

        # determine heights of each chain which bootstrap starts from
        for chain_index in self.supported_chain_list:
            chain_manager = self.get_chain_manager_of(chain_index)
            if chain_index == SwitchableChain.BIFROST:
                chain_manager.latest_height = bootstrap_start_height
            else:
                chain_manager.latest_height = find_height_by_timestamp(chain_manager, bootstrap_start_time)

        btc_logger = Logger("Bootstrap", logging.INFO)
        btc_logger.info("BIFROST's {}: version({})".format(self.role, __version__))
        if self.role == "Slow-relayer":
            btc_logger.info("Aggregated relay delay(sec): {}".format(RbcEvent.AGGREGATED_DELAY_SEC))
        btc_logger.info("Relayer-has-been-launched ({})".format(self.active_account.address.hex()))

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
