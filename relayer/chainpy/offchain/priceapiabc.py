from abc import ABCMeta, abstractmethod
from typing import List, Union, Dict
import json
import requests

from .utils import to_list
from ..eth.ethtype.amount import EthAmount

AnchorSym, Symbol, QueryId, Market = str, str, str, dict
MarketData = Dict[Symbol, Dict[str, EthAmount]]
MergedMargetData = Dict[Symbol, List[Dict[str, EthAmount]]]
Prices = Dict[Symbol, EthAmount]


class PriceApiABC(metaclass=ABCMeta):
    def __init__(self, api_base_url: str, request_timeout_sec: int = 120):
        self._api_base_url = api_base_url
        self._request_timeout_sec = request_timeout_sec

    def _request(self, api_url: str, params: dict = None, api_url_has_params=False):
        if params:
            api_url += '&' if api_url_has_params else '?'
            for key, value in params.items():
                if type(value) == bool:
                    value = str(value).lower()

                api_url += "{0}={1}&".format(key, value)
            api_url = api_url[:-1]

        result = requests.get(api_url, timeout=self._request_timeout_sec)
        result.raise_for_status()
        return json.loads(result.content.decode("utf-8"))

    @property
    def base_url(self) -> str:
        return self._api_base_url

    def check_supported(self, symbols: List[Symbol]) -> bool:
        supported_symbols = self.supported_symbols()
        for symbol in symbols:
            if symbol not in supported_symbols:
                return False
        return True

    @abstractmethod
    def ping(self) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def supported_symbols() -> List[Symbol]:
        pass

    @abstractmethod
    def _fetch_price_and_volume(self, symbols: List[Symbol]) -> MarketData:
        pass

    def get_current_price(self, symbols: Union[List[Symbol], Symbol]) -> MarketData:
        prices_and_volumes = self.get_current_price_and_volume(symbols)

        values = prices_and_volumes.values()
        for value in values:
            del value["volume"]

        return prices_and_volumes

    def get_current_price_and_volume(self, symbols: Union[Symbol, List[Symbol]]) -> MarketData:
        symbols = to_list(symbols)
        symbols = [symbol.upper() for symbol in symbols]

        if not self.check_supported(symbols):
            raise Exception("Not supported symbols: {}".format(symbols))

        return self._fetch_price_and_volume(symbols)
