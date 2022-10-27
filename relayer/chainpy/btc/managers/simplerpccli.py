import json
import unittest
from time import sleep

import requests
from requests.auth import HTTPBasicAuth
from typing import Union, Optional


BITCOIN_CONFIRMATION_HEIGHT = 6


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

    def _send_request(self, method: str, params: list) -> Union[dict, str, int]:
        """ Send rpc request to bitcoin-core without sending-wallet option. """
        body = {
            "jsonrpc": "1.0",
            "method": method,
            "params": params,
            "id": 1
        }

        resp = requests.post(self.url, json=body, auth=self.__rpc_auth)
        try:
            resp_json = resp.json()
        except json.decoder.JSONDecodeError as e:
            sleep(60)
            print("re-run after sleeping 60 secs")
            return self._send_request(method, params)

        if resp_json.get("result") is None:
            raise Exception("None result")
        elif resp.status_code != 200:
            raise Exception("rpc fails: {}".format(resp_json["error"]))
        else:
            return resp_json["result"]

    # get block hash
    def get_block_hash_by_height(self, height: int) -> str:
        result = self._send_request("getblockhash", [height])
        if not isinstance(result, str):
            raise Exception("Not allowed type of result: {}".format(type(result)))
        return result

    # get block
    def get_block_by_hash(self, block_hash: str, verbose: int = 1) -> Union[dict, str]:
        if not isinstance(verbose, int):
            raise Exception("Only allowed integer verbosity: serializedHex(0), blockWithTxHashes(1), blockWithTx(2)")
        result = self._send_request("getblock", [block_hash, verbose])
        if not isinstance(result, str) and not isinstance(result, dict):
            raise Exception("Not allowed type of result: {}".format(type(result)))
        return result

    def get_block_by_height(self, height: int, verbose: int = 1) -> dict:
        block_hash = self.get_block_hash_by_height(height)
        return self.get_block_by_hash(block_hash, verbose)

    # get block header
    def get_header_by_hash(self, block_hash: str, verbose: bool = False) -> Union[dict, str]:
        result = self._send_request("getblockheader", [block_hash, verbose])
        if not isinstance(result, str) and not isinstance(result, dict):
            raise Exception("Not allowed type of result: {}".format(type(result)))
        return result

    def get_header_by_height(self, height: int, verbose: bool = False) -> Union[dict, str]:
        block_hash = self.get_block_hash_by_height(height)
        return self.get_header_by_hash(block_hash, verbose)

    # get best block height
    def get_best_height(self) -> int:
        result = self._send_request("getblockcount", [])
        if not isinstance(result, int):
            raise Exception("Not allowed type of result: {}".format(type(result)))
        return result

    def get_best_block_hash(self) -> str:
        result = self._send_request("getbestblockhash", [])
        if not isinstance(result, str):
            raise Exception("Not allowed type of result: {}".format(type(result)))
        return result

    def get_best_block(self, verbose: int = 1) -> dict:
        block_hash = self.get_best_block_hash()
        return self.get_block_by_hash(block_hash, verbose)

    def get_best_header(self) -> Union[dict, str]:
        block_hash = self.get_best_block_hash()
        return self.get_header_by_hash(block_hash)

    def get_latest_confirmed_height(self) -> int:
        best_height = self.get_best_height()
        return best_height - BITCOIN_CONFIRMATION_HEIGHT

    def get_latest_confirmed_block_hash(self) -> str:
        confirmed_height = self.get_latest_confirmed_height()
        return self.get_block_hash_by_height(confirmed_height)

    def get_latest_confirmed_block(self, verbose: int = 1) -> dict:
        confirmed_height = self.get_latest_confirmed_height()
        return self.get_block_by_height(confirmed_height, verbose)

    def get_latest_confirmed_block_header(self, verbose: bool = False) -> dict:
        confirmed_height = self.get_latest_confirmed_height()
        return self.get_header_by_height(confirmed_height, verbose)
