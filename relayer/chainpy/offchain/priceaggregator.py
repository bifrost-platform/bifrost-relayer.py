import copy
import unittest
from enum import Enum
from typing import List, Union, Dict, Optional, Callable

from .priceapiabc import PriceApiABC, Symbol, MergedMargetData, Prices
from .utils import to_list, get_urls_from_private_config
from ..eth.ethtype.amount import eth_amount_avg, eth_amount_weighted_sum, EthAmount
from .chainlinkapi import ChainlinkApi
from .coingeckoapi import CoingeckoApi
from .upbitapi import UpbitApi


class PriceSrcIndex(Enum):
    COINGECKO = 1
    UPBIT = 2
    CHAINLINK = 3
    BINANCE = 4

    @staticmethod
    def from_name(name: str) -> Optional["PriceSrcIndex"]:
        for idx in PriceSrcIndex:
            if idx.name == name.upper():
                return idx
        return None

    @staticmethod
    def api_selector(src_name: str) -> Callable:
        normalized_name = src_name.capitalize()
        if normalized_name == "Coingecko":
            return CoingeckoApi
        if normalized_name == "Upbit":
            return UpbitApi
        if normalized_name == "Chainlink":
            return ChainlinkApi
        # if normalized_name == "Binance":
        #     return BinanceApi
        raise Exception("Not supported api name: {}".format(src_name))


class PriceOracleAgg:
    def __init__(self, source_names: list, url: dict):
        self.apis: Dict[PriceSrcIndex, PriceApiABC] = dict()

        for name in source_names:
            src_index = PriceSrcIndex.from_name(name)
            api = PriceSrcIndex.api_selector(name)
            self.apis[src_index] = api(url[name])

        self.__supported_symbols_each: Dict[PriceSrcIndex, List[Symbol]] = {}
        self.__supported_symbol_union: List[Symbol] = []
        for idx, api in self.apis.items():
            supported_symbols = api.supported_symbols()
            self.__supported_symbols_each[idx] = supported_symbols
            self.__supported_symbol_union += supported_symbols
        self.__supported_symbol_union = list(set(self.__supported_symbol_union))

    def ping(self) -> bool:
        for api in self.apis.values():
            if not api.ping():
                return False
        return True

    @property
    def supported_api_indices(self) -> List[PriceSrcIndex]:
        return list(self.apis.keys())

    @property
    def supported_apis(self) -> List[PriceApiABC]:
        return list(self.apis.values())

    @property
    def supported_symbols(self) -> List[Symbol]:
        return self.__supported_symbol_union

    @property
    def supported_symbols_each(self):
        return self.__supported_symbols_each

    def get_apis_supporting_symbol(self, symbol: Symbol) -> List[PriceSrcIndex]:
        apis = list()
        for idx, symbols in self.supported_symbols_each.items():
            if symbol in symbols:
                apis.append(idx)
        return apis

    @staticmethod
    def _merge_price_table(src_table: dict, dst_table: dict) -> Dict[Symbol, List[Dict[str, EthAmount]]]:
        src_clone = copy.deepcopy(src_table)
        for symbol in dst_table.keys():
            src_item = src_table.get(symbol)
            if src_item is None:
                src_clone[symbol] = [dst_table[symbol]]
            elif isinstance(src_item, dict):
                src_clone[symbol] = [src_item, dst_table[symbol]]
            elif isinstance(src_item, list):
                src_clone[symbol].append(dst_table[symbol])
            else:
                raise Exception("error")
        return src_clone

    def fetch_prices_and_volumes(self, symbols: Union[Symbol, List[Symbol]]) -> MergedMargetData:
        # ensure symbols is list
        symbols = to_list(symbols)
        symbols = [symbol.upper() for symbol in symbols]

        # ensure every symbol are supported
        for symbol in symbols:
            if symbol not in self.supported_symbols:
                raise Exception("Not allowed token symbol({}), select tokens in {}".format(
                    symbol,
                    self.supported_symbols
                ))

        # key: api index, value: symbols supported by the api
        classified_symbols_by_apis: Dict[PriceSrcIndex, List[Symbol]] = {}
        for idx, api in self.apis.items():
            classified_symbols_by_apis[idx] = list(set(api.supported_symbols()).intersection(symbols))

        # key: symbol, value: list of "PriceAndVolume"s from the api
        price_and_volume_table = {}
        for api_idx, api_symbols in classified_symbols_by_apis.items():
            try:
                prices_and_volumes = self.apis[api_idx].get_current_price_and_volume(api_symbols)
            except Exception as e:
                print("[Err] Api Error: {}\n  - msg: {}".format(api_idx.name, e))
                continue

            price_and_volume_table = self._merge_price_table(price_and_volume_table, prices_and_volumes)

        for symbol in symbols:
            if price_and_volume_table.get(symbol) is None:
                price_and_volume_table[symbol] = [{"price": EthAmount.zero(), "volume": EthAmount.zero()}]

        return price_and_volume_table

    def _rearrange_prices_and_volumes(self,
                                      symbols: Union[Symbol, List[Symbol]]) \
            -> (Dict[Symbol, List[EthAmount]], Dict[Symbol, List[EthAmount]]):
        price_and_volume_table: MergedMargetData = self.fetch_prices_and_volumes(symbols)

        symbol_prices: Dict[Symbol, List[EthAmount]] = {}
        symbol_volumes: Dict[Symbol, List[EthAmount]] = {}
        for symbol, prices_and_volumes in price_and_volume_table.items():
            if symbol_prices.get(symbol) is None:
                symbol_prices[symbol] = []

            if symbol_volumes.get(symbol) is None:
                symbol_volumes[symbol] = []

            for price_and_volume in prices_and_volumes:
                symbol_prices[symbol].append(price_and_volume["price"])
                symbol_volumes[symbol].append(price_and_volume["volume"])
        return symbol_prices, symbol_volumes

    def get_current_weighted_price(self, symbols: Union[Symbol, List[Symbol]]) -> Prices:
        symbol_prices, symbol_volumes = self._rearrange_prices_and_volumes(symbols)

        symbol_price: Prices = {}
        for symbol in symbols:
            symbol_price[symbol] = eth_amount_weighted_sum(symbol_prices[symbol], symbol_volumes[symbol])
        return symbol_price

    def get_current_averaged_price(self, symbols: Union[Symbol, List[Symbol]]) -> Prices:
        symbol_prices, _ = self._rearrange_prices_and_volumes(symbols)

        symbol_price: Prices = {}
        for symbol in symbols:
            symbol_price[symbol] = eth_amount_avg(symbol_prices[symbol])
        return symbol_price


class TestPriceAggregator(unittest.TestCase):
    def setUp(self) -> None:
        urls = get_urls_from_private_config()
        self.symbols = ["ETH", "BFC", "MATIC", "BNB", "USDC", "USDT", "BUSD", "KLAY", "BIFI", "BTC"]
        self.source_names = ["Coingecko", "Upbit", "Chainlink"]
        self.agg = PriceOracleAgg(self.source_names, urls)

    def test_coin_list(self):
        supported_symbols = self.agg.supported_symbols
        self.assertEqual(type(supported_symbols), list)

    def test_get_current_price(self):
        result = self.agg.fetch_prices_and_volumes(self.symbols)
        print(result)

    def test_get_current_weighted_price(self):
        print()
        prices = self.agg.get_current_weighted_price(self.symbols)
        for key, result in prices.items():
            print("{}-> price: {}".format(key, result))

    def test_get_current_averaged_price(self):
        results = self.agg.get_current_averaged_price(self.symbols)
        for key, result in results.items():
            print("{}-> price: {}".format(key, result))

    # def test_stress(self):
    #     for i in range(22):
    #         results = self.agg.get_current_averaged_price(self.symbols)
    #         print(results)
