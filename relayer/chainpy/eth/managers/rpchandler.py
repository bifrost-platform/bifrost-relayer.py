import logging

import requests
import time
from typing import List, Optional, Union, Callable

from .configs import EntityRootConfig
from ..ethtype.amount import EthAmount
from ..ethtype.consts import ChainIndex
from ..ethtype.hexbytes import EthAddress, EthHashBytes, EthHexBytes
from ..ethtype.chaindata import EthBlock, EthTransaction, EthReceipt, EthLog
from ..ethtype.exceptions import *
from ...logger import Logger, formatted_log

rpc_logger = Logger("RPC-Client", logging.INFO)


def _reduce_height_to_matured_height(matured_max_height: int, height: Union[int, str]) -> str:
    if height == "latest":
        height = 2 ** 256 - 1
    if isinstance(height, int):
        return hex(min(height, matured_max_height))
    raise Exception("height should be integer or \"latest\"")


def _hex_height_or_latest(height: Union[int, str] = "latest") -> str:
    if height == "latest":
        return height
    if isinstance(height, int):
        return hex(height)
    raise Exception("height should be integer or \"latest\"")


class EthRpcClient:
    ANALYZER_RELAYER = False
    CALL_NUM = {
        ChainIndex.BIFROST: 0,
        ChainIndex.ETHEREUM: 0,
        ChainIndex.BINANCE: 0,
        ChainIndex.POLYGON: 0,
        ChainIndex.KLAYTN: 0
    }
    TIME_CACHE = 0
    PRINT_PERIOD_SEC = 5

    # TODO research
    #  eth_newFilter, eth_getFilterChanges, eth_newBlockFilter(notify when a new block arrives)
    def __init__(self, chain_index: ChainIndex, root_config: EntityRootConfig):
        chain_config = root_config.get_chain_config(chain_index)
        self.__chain_index = chain_index
        self.__url_with_access_key = chain_config.url_with_access_key
        self.__receipt_max_try = chain_config.receipt_max_try
        self.__block_period_sec = chain_config.block_period_sec
        self.__block_aging_period = chain_config.block_aging_period

        self.__rpc_server_downtime_allow_sec = chain_config.rpc_server_downtime_allow_sec

        # check connection
        resp = self.send_request("eth_chainId", [])
        self.__chain_id = int(resp, 16)

    @classmethod
    def from_config_file(cls,
                         chain_index: ChainIndex,
                         public_config: str,
                         private_config: str = None,
                         project_root: str = "./"):
        root_config = EntityRootConfig.from_config_files(public_config, private_config, project_root)
        return cls(chain_index, root_config)

    @classmethod
    def from_config_dict(cls,
                         chain_index: ChainIndex,
                         public_config: dict,
                         private_config: dict = None,
                         project_root: str = "./"):
        root_config = EntityRootConfig.from_dict(public_config, private_config, project_root)
        return cls(chain_index, root_config)

    @property
    def url(self) -> str:
        return self.__url_with_access_key

    def send_request(self, method: str, params: list, endure: bool = True) -> Optional[Union[dict, str]]:
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        headers = {'Content-type': 'application/json'}
        response_json = None

        try:
            response_json = requests.post(self.url, json=body, headers=headers).json()
        except Exception as e:
            """ expected error: HttpsConnection """
            if endure:
                # sleep and re-request
                formatted_log(rpc_logger, log_data=str(e))
                print("request will be re-tried after {} secs".format(self.__rpc_server_downtime_allow_sec))
                time.sleep(self.__rpc_server_downtime_allow_sec)
                print("let's try it again!")
                return self.send_request(method, params, False)

        if response_json is not None:
            try:
                return response_json["result"]
            except KeyError as e:
                raise KeyError(response_json["error"])
        else:
            raise Exception("rpc_error: requests.post returns None without any exceptions")

    @property
    def chain_index(self) -> ChainIndex:
        """ return chain index specified from the configuration. """
        return self.__chain_index

    @property
    def chain_id(self) -> int:
        """ return chain id emitted by the rpc node. """
        return self.__chain_id

    def _reduce_heights_to_matured_height(self, heights: Union[list, int, str]) -> Union[List[str], str]:
        """
        reduce heights whenever each height is bigger than matured height.
        note that matured height means the maximum confirmed block height.
        """
        latest_block_height = self.eth_get_latest_block_number()
        matured_max_height = latest_block_height - self.__block_aging_period

        if not isinstance(heights, list):
            # for single height
            return _reduce_height_to_matured_height(matured_max_height, heights)
        else:
            # for multi heights
            amended_heights = list()
            for height in heights:
                amended_height = _reduce_height_to_matured_height(matured_max_height, height)
                amended_heights.append(amended_height)
            return amended_heights

    def eth_get_latest_block_number(self) -> int:
        """ returns the latest block height. """
        resp = self.send_request("eth_blockNumber", list())
        return int(resp, 16)

    def eth_get_matured_block_number(self) -> int:
        """ queries the latest block height and returns matured block height."""
        latest_height = self.eth_get_latest_block_number()
        return latest_height - self.__block_aging_period

    def eth_get_latest_block(self, verbose: bool = False) -> EthBlock:
        resp = self.send_request("eth_getBlockByNumber", ["latest", verbose])
        return EthBlock.from_dict(resp)

    def eth_get_balance(self, address: EthAddress, height: Union[int, str] = "latest") -> EthAmount:
        """ queries matured balance of the user. """
        if not isinstance(address, EthAddress):
            raise Exception("address type must be \"EthAddress\" type")
        matured_height = self._reduce_heights_to_matured_height(height)
        resp = self.send_request("eth_getBalance", [address.hex(), matured_height])
        return EthAmount(resp)

    def _get_block(self, method: str, params: list) -> Optional[EthBlock]:
        resp = self.send_request(method, params)
        return EthBlock.from_dict(resp)

    def _get_matured_block(self, method: str, params: list) -> Optional[EthBlock]:
        resp = self.send_request(method, params)
        fetched_block: EthBlock = EthBlock.from_dict(resp)
        if fetched_block.number > self.eth_get_matured_block_number():
            return None
        return fetched_block

    def eth_get_block_by_hash(self, block_hash: EthHashBytes, verbose: bool = False) -> Optional[EthBlock]:
        if not isinstance(block_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(block_hash))
        return self._get_block("eth_getBlockByHash", [block_hash.hex(), verbose])

    def eth_get_block_by_height(self, height: Union[int, str] = "latest", verbose: bool = False) -> Optional[EthBlock]:
        height_hex_or_latest = _hex_height_or_latest(height)
        return self._get_block("eth_getBlockByNumber", [height_hex_or_latest, verbose])

    def _get_transaction(self, method: str, params: list) -> Optional[EthTransaction]:
        resp = self.send_request(method, params)
        fetched_tx: EthTransaction = EthTransaction.from_dict(resp)
        if fetched_tx.block_number > self.eth_get_matured_block_number():
            return None
        return fetched_tx

    def eth_get_transaction_by_hash(self, tx_hash: EthHashBytes) -> Optional[EthTransaction]:
        if not isinstance(tx_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(tx_hash))
        return self._get_transaction("eth_getTransactionByHash", [tx_hash.hex()])

    def eth_get_transaction_by_height_and_index(self, height: int, tx_index: int) -> Optional[EthTransaction]:
        if not isinstance(height, int):
            raise EthTypeError(int, type(height))
        if not isinstance(tx_index, int):
            raise EthTypeError(int, type(tx_index))
        return self._get_transaction("eth_getTransactionByBlockNumberAndIndex", [hex(height), hex(tx_index)])

    def eth_get_transaction_by_hash_and_index(self,
                                              block_hash: EthHashBytes,
                                              tx_index: int) -> Optional[EthTransaction]:
        if not isinstance(block_hash, EthHashBytes):
            raise EthTypeError(EthHashBytes, type(block_hash))
        if not isinstance(tx_index, int):
            raise EthTypeError(int, type(tx_index))
        return self._get_transaction("eth_getTransactionByBlockHashAndIndex", [block_hash.hex(), hex(tx_index)])

    def _get_matured_receipt(self, tx_hash: EthHashBytes) -> Optional[EthReceipt]:
        resp = self.send_request('eth_getTransactionReceipt', [tx_hash.hex()])

        if resp is None:
            return None
        fetched_receipt: EthReceipt = EthReceipt.from_dict(resp)
        if fetched_receipt.block_number > self.eth_get_matured_block_number():
            return None
        return fetched_receipt

    def _get_receipt(self, tx_hash: EthHashBytes) -> Optional[EthReceipt]:
        resp = self.send_request('eth_getTransactionReceipt', [tx_hash.hex()])
        if resp is not None:
            return EthReceipt.from_dict(resp)

    def eth_receipt_without_wait(self, tx_hash: EthHashBytes, matured: bool = True) -> Optional[EthReceipt]:
        get_receipt_func: Callable = self._get_matured_receipt if matured else self._get_receipt
        return get_receipt_func(tx_hash)

    def eth_receipt_with_wait(self, tx_hash: EthHashBytes, matured: bool = True) -> Optional[EthReceipt]:
        get_receipt_func: Callable = self._get_matured_receipt if matured else self._get_receipt
        for i in range(self.__receipt_max_try):
            receipt = get_receipt_func(tx_hash)
            if receipt is not None:
                return receipt
            print("sleep {} sec".format(self.__block_period_sec / 2))  # TODO remove
            time.sleep(self.__block_period_sec / 2)  # wait half block
        return None

    def eth_get_logs(self,
                     from_block: int, to_block: int,
                     addresses: List[EthAddress], topics: List[EthHashBytes]) -> List[EthLog]:
        """ find logs of the event (which have topics) from multiple contracts """
        if from_block > to_block:
            raise Exception("from_block should be less than to_block")

        amended_block_nums = self._reduce_heights_to_matured_height([from_block, to_block])

        params: list = [{
            "fromBlock": amended_block_nums[0],
            "toBlock": amended_block_nums[1],
            "address": [address.with_checksum() for address in addresses],
            "topics": [topic.hex() for topic in topics]
        }]
        resp = self.send_request("eth_getLogs", params)
        try:
            return [EthLog.from_dict(log) for log in resp]
        except KeyError:
            raise RpcExceedRequestTime("Node: getLog time out")

    # **************************************** fee data ************************************************
    def eth_get_priority_fee_per_gas(self) -> int:
        resp = self.send_request("eth_maxPriorityFeePerGas", [])
        return int(resp, 16)

    def eth_get_next_base_fee(self) -> Optional[int]:
        block = self.eth_get_latest_block(verbose=False)

        current_base_fee = block.base_fee_per_gas
        if current_base_fee is None:
            return None

        block_gas_limit_half = block.gas_limit // 2
        max_base_fee_change_rate = 0.125
        current_block_gas = block.gas_used

        gas_offset = current_block_gas - block_gas_limit_half
        gas_offset_rate = gas_offset / block_gas_limit_half
        gas_change_rate = gas_offset_rate * max_base_fee_change_rate
        next_base_fee = current_base_fee * (1 + gas_change_rate)
        return int(next_base_fee)

    def eth_get_gas_price(self) -> int:
        resp = self.send_request("eth_gasPrice", [])
        return int(resp, 16)

    # **************************************** basic method ************************************************
    def eth_call(self, call_tx: dict) -> EthHexBytes:
        resp = self.send_request('eth_call', [call_tx, "latest"])
        return EthHexBytes(resp)

    def eth_estimate_gas(self, tx: dict):
        resp = self.send_request("eth_estimateGas", [tx, "latest"])
        return int(resp, 16)

    # matured height 적용하지 않음.
    def eth_get_user_nonce(self, address: EthAddress, height: Union[int, str] = "latest") -> int:
        height_hex_or_latest = _hex_height_or_latest(height)
        if not isinstance(address, EthAddress):
            raise Exception("address type must be \"EthAddress\" type")
        resp = self.send_request("eth_getTransactionCount", [address.hex(), height_hex_or_latest])
        return int(resp, 16)

    def eth_send_raw_transaction(self, signed_serialized_tx: EthHexBytes):
        # TODO impl, but low priority
        pass

    def eth_get_storage_at(self):
        # TODO impl, but low priority
        pass

    def eth_get_code(self, addr: EthAddress):
        # TODO impl, but low priority
        pass
