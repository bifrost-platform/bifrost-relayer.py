import requests
from requests.auth import HTTPBasicAuth
from typing import Union, Optional

from relayer.chainpy.btc.managers.header import BtcHeader
from relayer.chainpy.eth.ethtype.hexbytes import EthHexBytes, EthHashBytes


class SimpleBtcClient:
    def __init__(self, url: str, block_aging_period: int = 1, basic_auth_id: str = None, basic_auth_passwd: str = None):
        self.__url = url
        self.__block_aging_period = block_aging_period

        # basic auth setting
        if basic_auth_id is not None:
            self.__rpc_auth = HTTPBasicAuth(basic_auth_id, basic_auth_passwd)
        else:
            self.__rpc_auth = None

    @classmethod
    def from_config_dict(cls, config_dict: dict):
        url = config_dict["url"]
        basic_auth_id = config_dict.get("id")
        basic_auth_passwd = config_dict.get("passwd")
        if not basic_auth_id:
            basic_auth_id, basic_auth_passwd = None, None
        return cls(url, basic_auth_id, basic_auth_passwd)

    @property
    def url(self) -> str:
        return self.__url

    def _send_request(self, method: str, params: list) -> Optional[Union[dict, str]]:
        """ Send rpc request to bitcoin-core without sending-wallet option. """
        body = {
            "jsonrpc": "1.0",
            "method": method,
            "params": params,
            "id": 1
        }

        resp = requests.post(self.url, json=body, auth=self.__rpc_auth)
        resp_json = resp.json()
        if resp.status_code == 200:
            return resp_json["result"]
        else:
            raise Exception("rpc fails: {}".format(resp_json["error"]))

    # get block
    def get_block_by_hash(self, block_hash: str, verbose: int = 1) -> dict:
        return self._send_request("getblock", [block_hash, verbose])

    # get block hash
    def get_block_hash_by_height(self, height: int) -> str:
        return self._send_request("getblockhash", [height])

    # get block
    def get_block_by_height(self, height: int, verbose: int = 1) -> dict:
        block_hash = self.get_block_hash_by_height(height)
        return self.get_block_by_hash(block_hash, verbose)

    # get block header
    def get_block_header_by_hash(self, block_hash: str, verbose: bool = False) -> Union[BtcHeader, EthHexBytes]:
        result = self._send_request("getblockheader", [block_hash, verbose])
        if verbose:
            return BtcHeader.from_dict(result)
        else:
            return EthHexBytes(result)

    def get_block_header_by_height(self, height: int, verbose: bool = False) -> Union[BtcHeader, EthHexBytes]:
        block_hash = self.get_block_hash_by_height(height)
        return self.get_block_header_by_hash(block_hash, verbose)

    # get block hash
    def get_latest_block_hash(self) -> EthHashBytes:
        result = self._send_request("getbestblockhash", list())
        return EthHashBytes(result)

    def get_latest_block(self, verbose: int = 1):
        block_hash = self.get_latest_block_hash()
        return self.get_block_by_hash(block_hash.hex_without_0x(), verbose)

    def get_latest_block_header(self, verbose: bool = False) -> Union[BtcHeader, EthHexBytes]:
        latest_block_hash = self.get_latest_block_hash()
        return self.get_block_header_by_hash(latest_block_hash.hex_without_0x(), verbose)

    def get_matured_block_header(self, verbose: bool = False):
        latest_block_hash = self.get_latest_block_hash()
        latest_header = self.get_block_header_by_hash(latest_block_hash.hex_without_0x(), True)

        matured_height = latest_header.height - self.__block_aging_period
        return self.get_block_header_by_height(matured_height, verbose)
