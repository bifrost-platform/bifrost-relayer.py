import argparse
import sys

from chainpy.eth.ethtype.hexbytes import EthHexBytes
from rbclib.heartbeat import RelayerHeartBeat
from rbclib.chainevents import RbcEvent, ValidatorSetUpdatedEvent
from rbclib.periodicevents import PriceUpOracle, AuthDownOracle, BtcHashUpOracle
from relayer.metric import PrometheusExporterRelayer

from relayer.relayer import Relayer


parser = argparse.ArgumentParser(description="Relayer's launching package.")
parser.add_argument("-k", "--private-key", type=str, help="private key to be used by the relayer")
parser.add_argument("-c", "--config-path", type=str, help="insert configuration directory")
parser.add_argument("-a", "--private-config-path", type=str, help="insert sensitive configuration directory")
parser.add_argument("-b", "--no-heartbeat", action="store_true")
parser.add_argument("-p", "--prometheus", action="store_true")

DEFAULT_RELAYER_CONFIG_PATH = "configs/entity.relayer.json"
DEFAULT_PRIVATE_CONFIG_PATH = "configs/entity.relayer.private.json"


def main(_config: dict):
    secret_key = _config.get("private_key")
    secret_key_obj = EthHexBytes(secret_key)

    public_config_path, private_config_path = _config.get("config_path"), _config.get("private_config_path")
    if public_config_path is None:
        public_config_path = DEFAULT_RELAYER_CONFIG_PATH
    if private_config_path is None:
        private_config_path = DEFAULT_PRIVATE_CONFIG_PATH

    heart_beat_opt = True
    if _config.get("no_heartbeat"):
        heart_beat_opt = False

    prometheus_on = False
    if _config.get("prometheus"):
        prometheus_on = True

    # initiate relayer with two config file
    relayer = Relayer.init_from_config_files(
        public_config_path,
        private_config_path=private_config_path,
        private_key=secret_key_obj.hex() if isinstance(secret_key_obj, EthHexBytes) else None
    )

    # multichain monitor will detect "Socket" event from every socket contract.
    relayer.register_chain_event_obj("Socket", RbcEvent)

    # multichain monitor will detect "RoundUp" event from the socket contract on bifrost network.
    relayer.register_chain_event_obj("RoundUp", ValidatorSetUpdatedEvent)

    # event bridge will periodically check validator set of the bifrost network.
    relayer.register_offchain_event_obj("sync_validator", AuthDownOracle)

    # event bridge will periodically collect price source from offchain, and relay it to bifrost network.
    relayer.register_offchain_event_obj("price", PriceUpOracle)

    # event bridge will periodically collect bitcoin hash, and relay it to bifrost network.
    relayer.register_offchain_event_obj("btc_hash", BtcHashUpOracle)

    if heart_beat_opt:
        relayer.register_offchain_event_obj("heart_beat", RelayerHeartBeat)

    if prometheus_on:
        PrometheusExporterRelayer.init_prometheus_exporter_on_relayer()

    relayer.run_relayer()


if __name__ == "__main__":
    if not sys.argv[1:]:
        config = {
            "config_path": DEFAULT_RELAYER_CONFIG_PATH,
            "private_config_path": DEFAULT_PRIVATE_CONFIG_PATH,
            "no_heartbeat": True,
            "private_key": None,
            "prometheus": True
        }
    else:
        args = parser.parse_args()
        config = vars(args)

    main(config)
