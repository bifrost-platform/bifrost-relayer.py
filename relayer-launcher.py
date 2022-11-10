import argparse
import sys

from relayer.chainpy.eth.managers.rpchandler import EthRpcClient
from relayer.rbcevents.hearbeat import RelayerHeartBeat
from relayer.relayer import Relayer

from relayer.rbcevents.chainevents import RbcEvent, ValidatorSetUpdatedEvent
from relayer.rbcevents.periodicevents import PriceUpOracle, AuthDownOracle, BtcHashUpOracle
from relayer.chainpy.eth.ethtype.account import EthAccount


parser = argparse.ArgumentParser(description="Relayer's launching package.")

parser.add_argument("command", help="generate new private key, then export it as a PEM file")
parser.add_argument("-p", "--password", type=str, help="password to lock/unlock PEM file")
parser.add_argument("-s", "--pem", type=str, help="PEM file path (default: ./configs/private.pem)")
parser.add_argument("-k", "--existingKey", type=str, help="existing key to be used to generate a pem file")
parser.add_argument("-b", "--no-heartbeat", action="store_true")

RELAYER_CONFIG_PATH = "configs/entity.relayer.json"
PRIVATE_CONFIG_PATH = "configs/entity.relayer.private.json"
DEFAULT_PEM_PATH = "./configs/pems/private0.pem"


def main(_config: dict):
    cmd = config["command"]

    if cmd == "genkey":
        """ generate new private key, and then export it as a encrypted pem file. """
        pem_path = config.get("pem")
        pem_password = config.get("password")
        if pem_path is None or pem_password is None:
            raise Exception("PEM file path and password are required.")

        acc = EthAccount.generate()
        pem_str = acc.priv_to_pem(pem_password).decode()
        with open(pem_path, "w") as f:
            f.write(pem_str)

    elif cmd == "genpem":
        """ generate a pem file using existing key """
        pem_path = config.get("pem")
        pem_password = config.get("password")
        if pem_path is None or pem_password is None:
            raise Exception("PEM file path is required.")

        existing_key = config.get("existingKey")
        if existing_key is None:
            raise Exception("PEM file path and password are required.")

        acc = EthAccount.from_secret(existing_key)
        pem_str = acc.priv_to_pem(pem_password).decode()
        with open(pem_path, "w") as f:
            f.write(pem_str)

    elif cmd == "viewpem":
        pem_path = config.get("pem")
        pem_password = config.get("password")
        if pem_path is None or pem_password is None:
            raise Exception("PEM file path is required.")

        with open(pem_path, "r") as f:
            lines = f.readlines()
        decoded_pem = "".join(lines)
        print(decoded_pem)

    elif cmd == "launch":
        # parse private key from the pem file
        relayer = Relayer.init_from_config_files(
            RELAYER_CONFIG_PATH,
            private_config_path=PRIVATE_CONFIG_PATH,
            private_key=config.get("existingKey"),
            pem_path=config.get("pem"),
            password=config.get("password")
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

        # event bridge will periodically collect bitcoin hash, and relay it to bifrost network.

        no_hb = config.get("no_heartbeat")
        if not no_hb:
            relayer.register_offchain_event_obj("heart_bit", RelayerHeartBeat)

        if config.get("analyze") is not None:
            EthRpcClient.ANALYZER_RELAYER = True

        relayer.run_relayer()
    else:
        raise Exception("Not supported command: \"{}\"".format(cmd))


if __name__ == "__main__":
    if not sys.argv[1:]:
        config = {"command": "launch"}
    else:
        args = parser.parse_args()
        config = vars(args)
    main(config)
