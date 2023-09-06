import sys

from bridgeconst.consts import Chain


class ChainPrimitivesFactory:
    NONE = Chain.NONE
    BIFROST = Chain.BFC_MAIN
    ETHEREUM = Chain.ETH_MAIN
    BINANCE = Chain.BNB_MAIN
    MATIC = Chain.MATIC_MAIN
    AVALANCHE = Chain.AVAX_MAIN
    BASE = Chain.BASE_MAIN

    def __init__(self, test_flag: bool):
        if test_flag:
            self.switch_testnet_config()

    @classmethod
    def from_bytes(cls, value: bytes):
        return Chain.from_bytes(value)

    @classmethod
    def from_name(cls, name):
        return Chain.from_name(name)

    @classmethod
    def size(cls) -> int:
        return Chain.size()

    def switch_testnet_config(self):
        self.BIFROST = Chain.BFC_TEST
        self.ETHEREUM = Chain.ETH_GOERLI
        self.BINANCE = Chain.BNB_TEST
        self.MATIC = Chain.MATIC_MUMBAI
        self.AVALANCHE = Chain.AVAX_FUJI
        self.BASE = Chain.BASE_GOERLI


chain_primitives = ChainPrimitivesFactory('--testnet' in sys.argv[1:] or '-t' in sys.argv[1:])
