import argparse
import sys

from chainpy.eth.ethtype.hexbytes import EthHexBytes
from chainpy.eth.managers.configsanitycheck import is_meaningful
from chainpy.logger import logger_config_global, global_logger

from rbclib.aggchainevents import ExternalRbcEvents
from rbclib.heartbeat import RelayerHeartBeat
from rbclib.chainevents import RbcEvent, RoundUpEvent
from rbclib.periodicevents import PriceUpOracle, VSPFeed, BtcHashUpOracle
from rbclib.metric import PrometheusExporterRelayer
from rbclib.switchable_enum import SwitchableChain, SwitchableAsset

from relayer.relayer import Relayer, relayer_config_global, RelayerRole

parser = argparse.ArgumentParser(description="Relayer's launching package.")
parser.add_argument("-k", "--private-key", type=str, help="private key to be used by the relayer")
parser.add_argument("-c", "--config-path", type=str, help="insert configuration directory")
parser.add_argument("-a", "--private-config-path", type=str, help="insert sensitive configuration directory")
parser.add_argument("-b", "--no-heartbeat", action="store_true")
parser.add_argument("-p", "--prometheus", action="store_true")
parser.add_argument("-s", "--slow-relayer", action="store_true")
parser.add_argument("-f", "--fast-relayer", action="store_true")
parser.add_argument("-t", "--testnet", action="store_true")
parser.add_argument("-l", "--log-file-name", type=str)

DEFAULT_RELAYER_CONFIG_PATH = "configs/entity.relayer.json"
DEFAULT_PRIVATE_CONFIG_PATH = "configs/entity.relayer.private.json"

DEFAULT_TEST_RELAYER_CONFIG_PATH = "configs-testnet/entity.relayer.json"
DEFAULT_TEST_RELAYER_PRIVATE_CONFIG_PATH = "configs-testnet/entity.relayer.private.json"


def config_relayer(relayer: Relayer, heart_beat_opt: bool, prometheus_on: bool):
    # multichain monitor will detect "Socket" event from every socket contract.
    relayer.register_chain_event_obj("Socket", RbcEvent)

    # multichain monitor will detect "RoundUp" event from the socket contract on bifrost network.
    relayer.register_chain_event_obj("RoundUp", RoundUpEvent)

    # event bridge will periodically check validator set of the bifrost network.
    relayer.register_offchain_event_obj("sync_validator", VSPFeed)

    # event bridge will periodically collect price source from offchain, and relay it to bifrost network.
    relayer.register_offchain_event_obj("price", PriceUpOracle)

    # event bridge will periodically collect bitcoin hash, and relay it to bifrost network.
    relayer.register_offchain_event_obj("btc_hash", BtcHashUpOracle)

    if heart_beat_opt:
        relayer.register_offchain_event_obj("heart_beat", RelayerHeartBeat)

    if prometheus_on:
        PrometheusExporterRelayer.init_prometheus_exporter_on_relayer(relayer.supported_chain_list)


def config_fast_relayer(relayer: Relayer, prometheus_on: bool):
    # multichain monitor will detect "Socket" event from every socket contract.
    relayer.register_chain_event_obj("Socket", ExternalRbcEvents)

    # multichain monitor will detect "RoundUp" event from the socket contract on bifrost network.
    relayer.register_chain_event_obj("RoundUp", RoundUpEvent)

    if prometheus_on:
        PrometheusExporterRelayer.init_prometheus_exporter_on_relayer(relayer.supported_chain_list)

    relayer.role = "fast-relayer"
    relayer_config_global.relayer_role = RelayerRole.FAST_RELAYER


def determine_relayer_role(config: dict) -> RelayerRole:
    if config.get("fast_relayer") and config.get("slow_relayer"):
        raise Exception("launch relayer with not both options: -f and -s")

    if config.get("slow_relayer"):
        return RelayerRole.SLOW_RELAYER
    elif config.get("fast_relayer"):
        return RelayerRole.FAST_RELAYER
    else:
        return RelayerRole.GENERAL_RELAYER


def main(config: dict):
    is_test_config = True if config.get("testnet") else False

    log_file_name = config.get("log_file_name")
    if is_meaningful(log_file_name):
        # enable logger with file handler
        logger_config_global.reset(log_file_name=log_file_name, backup_count=8760)
    global_logger.init(log_file_name=log_file_name)

    # secret_key_obj is None if config["private_key"] is None
    secret_key_obj = EthHexBytes(config.get("private_key"))

    public_config_path, private_config_path = config.get("config_path"), config.get("private_config_path")
    if public_config_path is None:
        public_config_path = DEFAULT_RELAYER_CONFIG_PATH \
            if not is_test_config else DEFAULT_TEST_RELAYER_CONFIG_PATH
    if private_config_path is None:
        private_config_path = DEFAULT_PRIVATE_CONFIG_PATH \
            if not is_test_config else DEFAULT_TEST_RELAYER_PRIVATE_CONFIG_PATH

    # initiate relayer with two config file
    relayer = Relayer.init_from_config_files(
        public_config_path,
        private_config_path=private_config_path,
        private_key=secret_key_obj.hex() if isinstance(secret_key_obj, EthHexBytes) else None,
        role=determine_relayer_role(config)
    )

    heart_beat_opt = False if config.get("no_heartbeat") else True
    prometheus_on = True if config.get("prometheus") else False
    if config.get("fast_relayer"):
        config_fast_relayer(relayer, prometheus_on)
    else:
        config_relayer(relayer, heart_beat_opt, prometheus_on)

    relayer.run_relayer()


if __name__ == "__main__":
    if not sys.argv[1:]:
        _config = {
            'private_key': None,
            'config_path': None,
            'private_config_path': None,
            'no_heartbeat': False,
            'prometheus': False,
            'slow_relayer': True,
            'fast_relayer': False,
            'testnet': True,
            "log_file_name": "console.log"
        }
        if _config["testnet"]:
            # When testnet relay is launched via console, enums are automatically switched.
            SwitchableChain.switch_testnet_config()
            SwitchableAsset.switch_testnet_config()
    else:
        args = parser.parse_args()
        _config = vars(args)

    # print(_config)
    main(_config)
