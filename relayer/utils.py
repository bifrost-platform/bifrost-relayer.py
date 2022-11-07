import requests

from relayer.chainpy.eth.ethtype.account import EthAccount

RELAYER_VERSION = "v0.1.8"


class ImOnline:
    url = "https://leaderboard-api.testnet.thebifrost.io/user/health"

    @classmethod
    def send_request(cls, account: EthAccount) -> int:
        body = {
            "relayerAddress": account.address.hex(),
            "version": RELAYER_VERSION
        }
        response_json = requests.post(cls.url, json=body).json()
        return int(response_json["statusCode"])
