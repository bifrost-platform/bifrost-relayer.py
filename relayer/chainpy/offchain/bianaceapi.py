# import unittest
# from typing import List, Dict, Union, Optional
#
# from ..eth.ethtype.amount import EthAmount
# from ..offchain.priceapiabc import PriceApiABC, MarketId, Market, PriceAndVolume, Symbol, SymbolPrice
#
#
# # https://api.binance.com/api/v1/ticker/allPrices
# # https://api.binance.com/api/v3/ticker/24hr?symbols=[%22BNBUSDT%22,%22BNBBTC%22]
# class BinanceApi(PriceApiABC):
#     __API_URL_BASE = "https://api.binance.com/api/v3/"
#     __REQUEST_TIMEOUT_SEC = 120
#     __ANCHOR_COIN_IDS = ["USDT", "BTC", "KRW"]
#
#     def __init__(self, api_base_url: str = __API_URL_BASE, request_timeout_sec: int = __REQUEST_TIMEOUT_SEC):
#         super().__init__(api_base_url, request_timeout_sec)
#         self.__market_names: Optional[Dict[Symbol, List[Symbol]]] = None
#         self._caching_market_ids(["USDT-BTC", "KRW-BTC"])
#
#     def ping(self) -> bool:
#         api_url = "{}ping".format(self.base_url)
#         result = self._request(api_url)
#         return result == dict()
#
#     def symbols_to_market_ids(self, coin_id: Symbol) -> List[MarketId]:
#         pass
#
#     def _fetch_markets(self, market_ids: List[MarketId]) -> Market:
#         # tiker
#         pass
#
#     def get_supported_symbols(self) -> List[Symbol]:
#         # https: // api.binance.com / api / v3 / ticker / price
#         if self._supported_coin_list is None:
#             api_url = "{}ticker/price".format(self.base_url)
#             results = self._request(api_url)
#             supported_ids = list()
#
#             total = len(results)
#             market_name = ["BUSD", "USDT", "BNB", "BTC", "ETH", "XRP", "TRX", "DOGE", "DOT", "USD", "USDC", "PAX", "USDS", "AUD", "BKRW", "EUR", "BIDR", "TRY", "TUSD", "VAI", "BRL", "GBP", "RUB", "NGN", "UAH"]
#             others = list()
#             for result in results:
#                 symbol = result["symbol"]
#                 if symbol[:3] in market_name or symbol[:4] in market_name or symbol[-3:] in market_name or symbol[-4:] in market_name:
#                     pass
#                 else:
#                     others.append(symbol)
#             print("total: {}, others: {}, {}".format(total, len(others), others))
#
#     # def get_all_market_names(self):
#
#
#     def get_current_price(self, coin_ids: Union[List[Symbol], Symbol]) -> Dict[Symbol, SymbolPrice]:
#         pass
#
#     def get_current_price_and_volume(self, coin_ids: Union[List[Symbol], Symbol]) -> Dict[Symbol, PriceAndVolume]:
#         pass
#
#
# class TestBinanceApi(unittest.TestCase):
#     def setUp(self) -> None:
#         self.api = BinanceApi()
#
#     def test_ping(self):
#         result = self.api.ping()
#         self.assertTrue(result)
#
#     def test_coin_list(self):
#         coin_list = self.api.get_supported_symbols()
#         self.assertEqual(type(coin_list), list)
#
#     def test_price(self):
#         ids = ["BFC", "BTC", "FIL"]
#         prices_dict = self.api.get_current_price(ids)
#         for coin_id, price in prices_dict.items():
#             self.assertTrue(coin_id in ids)
#             self.assertEqual(type(price), EthAmount)
#
#     def test_price_and_volumes(self):
#         ids = ["bifrost"]
#         prices_and_volume_dict = self.api.get_current_price_and_volume(ids)
#         for coin_id, price_and_volume in prices_and_volume_dict.items():
#             self.assertTrue(coin_id in ids)
#             self.assertEqual(type(price_and_volume.price), EthAmount)
#             self.assertEqual(type(price_and_volume.volume), EthAmount)
#
#     def test_delete_cache(self):
#         ids = ["BFC"]
#         _ = self.api.get_supported_symbols()
#         _ = self.api.get_current_price(ids)
#         self.assertIsNotNone(self.api._market_data)
#         self.assertIsNotNone(self.api._supported_coin_list)
#         self.api.delete_cache()
#         self.assertIsNone(self.api._market_data)
#         self.assertIsNone(self.api._supported_coin_list)
