import sys

from bridgeconst.consts import Chain, Asset


class _SwitchableChain:
    def __init__(self, test_flag: bool):
        if test_flag:
            self.NONE = Chain.NONE
            self.BIFROST = Chain.BFC_TEST
            self.ETHEREUM = Chain.ETH_GOERLI
            self.BINANCE = Chain.BNB_TEST
            self.MATIC = Chain.MATIC_MUMBAI
            self.AVALANCHE = Chain.AVAX_FUJI
        else:
            self.NONE = Chain.NONE
            self.BIFROST = Chain.BFC_MAIN
            self.ETHEREUM = Chain.ETH_MAIN
            self.BINANCE = Chain.BNB_MAIN
            self.MATIC = Chain.MATIC_MAIN
            self.AVALANCHE = Chain.AVAX_MAIN

    @classmethod
    def from_bytes(cls, value: bytes):
        return Chain.from_bytes(value)

    @classmethod
    def from_name(cls, name):
        return Chain.from_name(name)

    @classmethod
    def size(cls) -> int:
        return Chain.size()


SwitchableChain = _SwitchableChain("--testnet" in sys.argv[1:])


class _SwitchableAsset:
    def __init__(self, test_flag: bool):
        if test_flag:
            self.NONE = Asset.NONE
            self.BFC_ON_BIFROST = Asset.BFC_ON_BFC_TEST
            self.BFC_ON_ETHEREUM = Asset.BFC_ON_ETH_GOERLI
            self.BRIDGED_ETHEREUM_BFC_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_BFC_ON_BFC_TEST
            self.UNIFIED_BFC_ON_BIFROST = Asset.UNIFIED_BFC_ON_BFC_TEST

            # BIFI--------------------------------------------------------------------------------------------------------------
            self.BIFI_ON_ETHEREUM = Asset.BIFI_ON_ETH_GOERLI
            self.BRIDGED_ETHEREUM_BIFI_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_BIFI_ON_BFC_TEST
            self.UNIFIED_BIFI_ON_BIFROST = Asset.UNIFIED_BIFI_ON_BFC_TEST

            # ETH---------------------------------------------------------------------------------------------------------------
            self.ETH_ON_ETHEREUM = Asset.ETH_ON_ETH_GOERLI
            self.BRIDGED_ETHEREUM_ETH_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_ETH_ON_BFC_TEST
            self.UNIFIED_ETHEREUM_ETH_ON_BIFROST = Asset.UNIFIED_ETH_ON_BFC_TEST

            # BNB---------------------------------------------------------------------------------------------------------------
            self.BNB_ON_BINANCE = Asset.BNB_ON_BNB_TEST
            self.BRIDGED_BNB_ON_BIFROST = Asset.BRIDGED_BNB_TEST_BNB_ON_BFC_TEST
            self.UNIFIED_BNB_ON_BIFROST = Asset.UNIFIED_BNB_ON_BFC_TEST

            # MATIC------------------------------------------------------------------------------------------------------------
            self.MATIC_ON_POLYGON = Asset.MATIC_ON_MATIC_MUMBAI
            self.BRIDGED_MATIC_ON_BIFROST = Asset.BRIDGED_MATIC_MUMBAI_MATIC_ON_BFC_TEST
            self.UNIFIED_MATIC_ON_BIFROST = Asset.UNIFIED_MATIC_ON_BFC_TEST

            # USDC
            # ------------------------------------------------------------------------------------------------------------------
            self.USDC_ON_ETHEREUM = Asset.USDC_ON_ETH_GOERLI
            self.USDC_ON_BINANCE = Asset.USDC_ON_BNB_TEST

            self.BRIDGED_ETHEREUM_USDC_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_USDC_ON_BFC_TEST
            self.BRIDGED_BINANCE_USDC_ON_BIFROST = Asset.BRIDGED_BNB_TEST_USDC_ON_BFC_TEST
            self.UNIFIED_USDC_ON_BIFROST = Asset.UNIFIED_USDC_ON_BFC_TEST
        else:
            self.NONE = Asset.NONE
            # BFC---------------------------------------------------------------------------------------------------------------
            self.BFC_ON_BIFROST = Asset.BFC_ON_BFC_MAIN
            self.BFC_ON_ETHEREUM = Asset.BFC_ON_ETH_MAIN
            self.BRIDGED_ETHEREUM_BFC_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_BFC_ON_BFC_MAIN
            self.UNIFIED_BFC_ON_BIFROST = Asset.UNIFIED_BFC_ON_BFC_MAIN

            # BIFI--------------------------------------------------------------------------------------------------------------
            self.BIFI_ON_ETHEREUM = Asset.BIFI_ON_ETH_MAIN
            self.BRIDGED_ETHEREUM_BIFI_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_BIFI_ON_BFC_MAIN
            self.UNIFIED_BIFI_ON_BIFROST = Asset.UNIFIED_BIFI_ON_BFC_MAIN

            # ETH---------------------------------------------------------------------------------------------------------------
            self.ETH_ON_ETHEREUM = Asset.ETH_ON_ETH_MAIN
            self.BRIDGED_ETHEREUM_ETH_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_ETH_ON_BFC_MAIN
            self.UNIFIED_ETHEREUM_ETH_ON_BIFROST = Asset.UNIFIED_ETH_ON_BFC_MAIN

            # BNB---------------------------------------------------------------------------------------------------------------
            self.BNB_ON_BINANCE = Asset.BNB_ON_BNB_MAIN
            self.BRIDGED_BNB_ON_BIFROST = Asset.BRIDGED_BNB_MAIN_BNB_ON_BFC_MAIN
            self.UNIFIED_BNB_ON_BIFROST = Asset.UNIFIED_BNB_ON_BFC_MAIN

            # MATIC------------------------------------------------------------------------------------------------------------
            self.MATIC_ON_POLYGON = Asset.MATIC_ON_MATIC_MAIN
            self.BRIDGED_MATIC_ON_BIFROST = Asset.BRIDGED_MATIC_MAIN_MATIC_ON_BFC_MAIN
            self.UNIFIED_MATIC_ON_BIFROST = Asset.UNIFIED_MATIC_ON_BFC_MAIN

            # USDC
            # ------------------------------------------------------------------------------------------------------------------
            self.USDC_ON_ETHEREUM = Asset.USDC_ON_ETH_MAIN
            self.USDC_ON_BINANCE = Asset.USDC_ON_BNB_MAIN

            self.BRIDGED_ETHEREUM_USDC_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_USDC_ON_BFC_MAIN
            self.BRIDGED_BINANCE_USDC_ON_BIFROST = Asset.BRIDGED_BNB_MAIN_USDC_ON_BFC_MAIN
            self.UNIFIED_USDC_ON_BIFROST = Asset.UNIFIED_USDC_ON_BFC_MAIN

    @classmethod
    def from_bytes(cls, value: bytes):
        return Asset.from_bytes(value)

    @classmethod
    def from_name(cls, name):
        return Asset.from_name(name)

    @classmethod
    def size(cls) -> int:
        return Asset.size()


SwitchableAsset = _SwitchableAsset("--testnet" in sys.argv[1:])
