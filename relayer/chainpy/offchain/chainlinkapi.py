import unittest
from typing import List

from .utils import get_url_from_private_config
from .chainlinkconst import eth_addresses_by_symbol
from .priceapiabc import PriceApiABC, Symbol, MarketData, QueryId
from ..eth.managers.rpchandler import EthRpcClient
from ..eth.ethtype.amount import EthAmount
from ..eth.ethtype.consts import ChainIndex


class ChainlinkApi(PriceApiABC):
    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        super().__init__(api_base_url, request_timeout_sec)

        config_dict = {
            "ethereum": {"chain_name": "ETHEREUM", "block_period_sec": 3, "url_with_access_key": api_base_url}
        }
        self.__rpc_cli = EthRpcClient.from_config_dict(ChainIndex.ETHEREUM, config_dict)

    def ping(self) -> bool:
        return isinstance(self.__rpc_cli.chain_id, int)

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(eth_addresses_by_symbol.keys())

    @staticmethod
    def _get_query_id_by_symbol(symbol: Symbol) -> QueryId:
        return eth_addresses_by_symbol[symbol]

    def _fetch_price_and_volume(self, symbols: List[Symbol]) -> MarketData:
        ret = {}
        for symbol in symbols:
            contract_address = eth_addresses_by_symbol[symbol]
            if contract_address == "0x0000000000000000000000000000000000000000":
                raise Exception("Not supported symbol (zero address): {}".format(symbols))
            result = self.__rpc_cli.eth_call({"to": contract_address, "data": "0xfeaf968c"})
            price = int.from_bytes(result[32:64], byteorder="big") * 10 ** 10
            ret[symbol] = {"price": EthAmount(price), "volume": EthAmount(0.0)}
        return ret


class TestChainLinkApi(unittest.TestCase):
    def setUp(self) -> None:
        url = get_url_from_private_config("Chainlink")
        self.api = ChainlinkApi(url)
        self.symbols = ["ETH", "BNB", "MATIC", "USDT", "USDC"]

    def test_ping(self):
        result = self.api.ping()
        self.assertTrue(result)

    def test_coin_list(self):
        coin_list = self.api.supported_symbols()
        self.assertEqual(type(coin_list), list)

    def test_price(self):
        prices_dict = self.api.get_current_price(self.symbols)
        for symbol, price in prices_dict.items():
            self.assertTrue(symbol in self.symbols)
            self.assertTrue(isinstance(price["price"], EthAmount))

    def test_price_and_volumes(self):
        prices_and_volume_dict = self.api.get_current_price_and_volume(self.symbols)
        for symbol, price_and_volume in prices_and_volume_dict.items():
            self.assertTrue(symbol in self.symbols)

            price = price_and_volume["price"]
            self.assertTrue(isinstance(price, EthAmount))
            self.assertNotEqual(price, EthAmount.zero())

            volume = price_and_volume["volume"]
            self.assertTrue(isinstance(volume, EthAmount))
            self.assertEqual(volume, EthAmount.zero())
