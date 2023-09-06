import argparse

from chainpy.eth.ethtype.hexbytes import EthHexBytes
from chainpy.logger import logger_config_global, global_logger

from rbclib.events.rbc_event import RbcEvent, ExternalRbcEvent
from rbclib.events.roundup_event import RoundUpEvent
from rbclib.metric import PrometheusExporterRelayer
from rbclib.periodic.heartbeat import RelayerHeartBeat
from rbclib.periodic.oracle_price_up import PriceUpOracle
from rbclib.periodic.vsp_feed import VSPFeed
from relayer.relayer import Relayer, relayer_config_global, RelayerRole

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

    # TODO: Back to code after fix btc hash oracle
    # # event bridge will periodically collect bitcoin hash, and relay it to bifrost network.
    # relayer.register_offchain_event_obj("btc_hash", BtcHashUpOracle)

    if heart_beat_opt:
        relayer.register_offchain_event_obj("heart_beat", RelayerHeartBeat)

    if prometheus_on:
        PrometheusExporterRelayer.init_prometheus_exporter_on_relayer(relayer.supported_chain_list)


def config_fast_relayer(relayer: Relayer, prometheus_on: bool):
    # multichain monitor will detect "Socket" event from every socket contract.
    relayer.register_chain_event_obj("Socket", ExternalRbcEvent)

    # multichain monitor will detect "RoundUp" event from the socket contract on bifrost network.
    relayer.register_chain_event_obj("RoundUp", RoundUpEvent)

    if prometheus_on:
        PrometheusExporterRelayer.init_prometheus_exporter_on_relayer(relayer.supported_chain_list)

    relayer.role = "fast-relayer"
    relayer_config_global.relayer_role = RelayerRole.FAST_RELAYER


def determine_relayer_role(config: dict) -> RelayerRole:
    if config['fast_relayer'] and config['slow_relayer']:
        raise Exception("launch relayer with not both options: -f and -s")

    if config['slow_relayer']:
        return RelayerRole.SLOW_RELAYER
    elif config['fast_relayer']:
        return RelayerRole.FAST_RELAYER
    else:
        return RelayerRole.GENERAL_RELAYER


def setup_logger(log_file_name: str):
    if log_file_name and log_file_name != '':
        # enable logger with file handler
        logger_config_global.reset(log_file_name=log_file_name, backup_count=8760)
    global_logger.init(log_file_name=log_file_name)


def setup_relayer(config: dict) -> Relayer:
    # Secret key handling
    secret_key = EthHexBytes(config['private_key'])

    # Configuration path handling
    public_config_path = config.get("config_path", DEFAULT_RELAYER_CONFIG_PATH)
    private_config_path = config.get("private_config_path", DEFAULT_PRIVATE_CONFIG_PATH)

    # Determine relayer role
    role = determine_relayer_role(config)

    # Initiate and configure the relayer
    relayer = Relayer.init_from_config_files(
        relayer_config_path=public_config_path,
        private_config_path=private_config_path,
        private_key=secret_key.hex() if isinstance(secret_key, EthHexBytes) else None,
        role=role
    )

    heart_beat_opt = not config.get("no_heartbeat", False)
    prometheus_on = config.get("prometheus", False)

    if config["fast_relayer"]:
        config_fast_relayer(relayer, prometheus_on)
    else:
        config_relayer(relayer, heart_beat_opt, prometheus_on)

    return relayer


def main():
    parser = argparse.ArgumentParser(description="Relayer's launching package.")
    parser.add_argument("-k", "--private-key", type=str, help="private key to be used by the relayer", default=None)
    parser.add_argument("-c", "--config-path", type=str, help="insert configuration directory", default=None)
    parser.add_argument("-a", "--private-config-path", type=str, help="insert sensitive configuration directory", default=None)
    parser.add_argument("-b", "--no-heartbeat", action="store_true", default=False)
    parser.add_argument("-p", "--prometheus", action="store_true", default=False)
    parser.add_argument("-s", "--slow-relayer", action="store_true", default=True)
    parser.add_argument("-f", "--fast-relayer", action="store_true", default=False)
    parser.add_argument("-t", "--testnet", action="store_true", default=True)
    parser.add_argument("-l", "--log-file-name", type=str, default='console.log')
    config = vars(parser.parse_args())

    setup_logger(config['log_file_name'])

    relayer = setup_relayer(config)
    relayer.run_relayer()


if __name__ == "__main__":
    main()
