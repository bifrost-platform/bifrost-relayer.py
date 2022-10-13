import unittest
from typing import List

import requests.exceptions

from .utils import get_url_from_private_config
from .priceapiabc import PriceApiABC, Market, Symbol, QueryId, MarketData
from .upbitconst import supported_symbols
from ..eth.ethtype.amount import EthAmount, eth_amount_weighted_sum, eth_amount_sum


class UpbitApi(PriceApiABC):
    ANCHOR_COIN_IDS = ["USDT", "BTC", "KRW"]

    def __init__(self, api_base_url: str, request_timeout_sec: int = 300):
        super().__init__(api_base_url, request_timeout_sec=request_timeout_sec)

    def ping(self) -> bool:
        result = self.get_current_price_and_volume("BTC")
        return isinstance(result["BTC"]["price"], EthAmount)

    @staticmethod
    def is_anchor(sym: Symbol) -> bool:
        return sym in UpbitApi.ANCHOR_COIN_IDS

    @staticmethod
    def supported_symbols() -> List[Symbol]:
        return list(supported_symbols.keys())

    @staticmethod
    def get_query_id_of_anchor(anchor_sym: Symbol) -> List[QueryId]:
        if anchor_sym == "USDT":
            return []
        if anchor_sym == "BTC":
            return ["USDT-BTC"]
        if anchor_sym == "KRW":
            return ["USDT-BTC", "KRW-BTC"]
        raise Exception("Invalid Anchor: {}".format(anchor_sym))

    @staticmethod
    def _get_query_id_by_symbol(symbol: Symbol) -> List[QueryId]:
        if UpbitApi.is_anchor(symbol):
            return UpbitApi.get_query_id_of_anchor(symbol)
        else:
            anchors = supported_symbols[symbol]
            return ["{}-{}".format(anchor, symbol) for anchor in anchors]

    @staticmethod
    def _get_price_in_market(market: Market) -> EthAmount:
        price = market["trade_price"]
        price_float = price / 1.0 if isinstance(price, int) else price
        return EthAmount(price_float)

    @staticmethod
    def _get_volume_in_market(market: Market) -> EthAmount:
        volume = market["acc_trade_price_24h"]
        volume_float = volume / 1.0 if isinstance(volume, int) else volume
        return EthAmount(volume_float)

    @staticmethod
    def _get_market_by_market_id(market_id: str, markets: list) -> Market:
        for market in markets:
            if market["market"] == market_id:
                return market
        raise Exception("No market matched with the market id")

    def _fetch_markets_by_symbols(self, symbols: List[Symbol]) -> List[Market]:
        query_ids = []
        for symbol in symbols:
            query_ids += self._get_query_id_by_symbol(symbol)

        anchors = sorted(list(set().union(*[supported_symbols[symbol] for symbol in symbols])))
        for anchor in anchors:
            query_ids += self.get_query_id_of_anchor(anchor)

        query_ids = sorted(list(set(query_ids)))
        query_ids = ",".join(query_ids)

        api_url = "{}ticker".format(self.base_url)
        return self._request(api_url, {"markets": query_ids})

    @staticmethod
    def _calc_anchor_price(anchor_sym: Symbol, markets: list) -> EthAmount:
        if anchor_sym == "USDT":
            return EthAmount(1.0)
        if anchor_sym == "BTC":
            market = UpbitApi._get_market_by_market_id("USDT-BTC", markets)
            return UpbitApi._get_price_in_market(market)
        if anchor_sym == "KRW":
            usdt_btc_market = UpbitApi._get_market_by_market_id("USDT-BTC", markets)
            krw_btc_market = UpbitApi._get_market_by_market_id("KRW-BTC", markets)
            btc_price_in_usd = UpbitApi._get_price_in_market(usdt_btc_market)
            return EthAmount(1.0) / UpbitApi._get_price_in_market(krw_btc_market) * btc_price_in_usd
        raise Exception("Not allowed anchor id: {}".format(anchor_sym))

    @staticmethod
    def _parse_market_by_symbol(symbol: Symbol, markets: list) -> List[Market]:
        ret = []
        for market in markets:
            if market["market"].split("-")[1] == symbol:
                ret.append(market)
        return ret

    @staticmethod
    def _calc_price_and_volume_in_usd(markets: List, anchor_prices: dict) -> (EthAmount, EthAmount):
        prices = []
        volumes = []
        for market in markets:
            anchor_sym, symbol = market["market"].split("-")
            anchor_price = anchor_prices[anchor_sym]
            price = UpbitApi._get_price_in_market(market) * anchor_price
            volume = UpbitApi._get_volume_in_market(market) * anchor_price

            prices.append(price)
            volumes.append(volume)

        price = eth_amount_weighted_sum(prices, volumes)
        volumes = eth_amount_sum(volumes)
        return price, volumes

    def _fetch_price_and_volume(self, symbols: List[Symbol]) -> MarketData:
        markets = self._fetch_markets_by_symbols(symbols)

        anchors = sorted(list(set().union(*[supported_symbols[symbol] for symbol in symbols])))
        anchor_prices = {}
        for anchor in anchors:
            anchor_prices[anchor] = UpbitApi._calc_anchor_price(anchor, markets)

        ret = {}
        for symbol in symbols:
            if symbol == "USDT":
                ret[symbol] = {"price": EthAmount(1.0), "volume": EthAmount(0.0)}
                continue
            target_markets = self._parse_market_by_symbol(symbol, markets)
            price, volume = self._calc_price_and_volume_in_usd(target_markets, anchor_prices)
            ret[symbol] = {"price": price, "volume": volume}

        return ret


class TestUpbitApi(unittest.TestCase):
    def setUp(self) -> None:
        url = get_url_from_private_config("Upbit")
        self.api = UpbitApi(url)
        self.symbols = ["ETH", "MATIC", "BFC", "USDT"]

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

    def test_stress(self):
        for i in range(22):
            try:
                results = self.api.get_current_price(self.symbols)
                print(results)
            except requests.exceptions.HTTPError as e:
                print(e)
