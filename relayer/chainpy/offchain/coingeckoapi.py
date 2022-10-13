import unittest
from typing import List, Union

from .utils import get_url_from_private_config
from ..eth.ethtype.amount import EthAmount
from ..offchain.coingeckoconst import supported_symbols
from ..offchain.priceapiabc import PriceApiABC, Market, to_list, Symbol, MarketData, QueryId


class CoingeckoApi(PriceApiABC):
    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        super().__init__(api_base_url, request_timeout_sec)

    def ping(self) -> bool:
        api_url = "{}ping".format(self.base_url)
        result = self._request(api_url)
        return result == {"gecko_says": "(V3) To the Moon!"}

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(supported_symbols.keys())

    @staticmethod
    def _get_query_id_by_symbol(symbol: Symbol) -> QueryId:
        return supported_symbols[symbol]

    @staticmethod
    def _get_price_in_market(market: Market) -> EthAmount:
        price = market["current_price"]
        if isinstance(price, int):
            price = price / 1.0  # casting to float
        return EthAmount(price)

    @staticmethod
    def _get_volume_in_market(market: Market) -> EthAmount:
        volume = market["total_volume"]
        if isinstance(volume, int):
            volume = volume / 1.0  # casting to float
        return EthAmount(volume)

    def _fetch_price_and_volume(self, symbols: List[Symbol]) -> MarketData:
        # get not cached coin id
        market_ids = [self._get_query_id_by_symbol(symbol) for symbol in symbols]
        req_ids = ",".join(market_ids)
        api_url = "{}coins/markets".format(self.base_url)

        ret = {}
        markets = self._request(api_url, {"ids": req_ids, "vs_currency": "usd"})
        for i, market in enumerate(markets):
            # find key by value on dictionary
            symbol = list(supported_symbols.keys())[list(supported_symbols.values()).index(market["id"])]
            price = self._get_price_in_market(market)
            volume = self._get_volume_in_market(market)
            ret[symbol] = {"price": price, "volume": volume}
        return ret


class TestCoinGeckoApi(unittest.TestCase):
    def setUp(self) -> None:
        url = get_url_from_private_config("Coingecko")
        self.api = CoingeckoApi(url)
        self.symbols = ["ETH", "BNB", "MATIC", "KLAY", "BFC", "USDT", "USDC", "BIFI"]

    def test_ping(self):
        result = self.api.ping()
        self.assertTrue(result)

    def test_coin_list(self):
        symbols = self.api.supported_symbols()
        self.assertEqual(type(symbols), list)

    def test_price(self):
        prices = self.api.get_current_price(self.symbols)
        for symbol, price in prices.items():
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
