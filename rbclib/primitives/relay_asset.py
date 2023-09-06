import sys

from bridgeconst.consts import Asset


class AssetPrimitivesFactory:
    NONE = Asset.NONE
    # BFC---------------------------------------------------------------------------------------------------------------
    BFC_ON_BIFROST = Asset.BFC_ON_BFC_MAIN
    BFC_ON_ETHEREUM = Asset.BFC_ON_ETH_MAIN
    BRIDGED_ETHEREUM_BFC_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_BFC_ON_BFC_MAIN
    UNIFIED_BFC_ON_BIFROST = Asset.UNIFIED_BFC_ON_BFC_MAIN

    # BIFI--------------------------------------------------------------------------------------------------------------
    BIFI_ON_ETHEREUM = Asset.BIFI_ON_ETH_MAIN
    BRIDGED_ETHEREUM_BIFI_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_BIFI_ON_BFC_MAIN
    UNIFIED_BIFI_ON_BIFROST = Asset.UNIFIED_BIFI_ON_BFC_MAIN

    # ETH---------------------------------------------------------------------------------------------------------------
    ETH_ON_ETHEREUM = Asset.ETH_ON_ETH_MAIN
    BRIDGED_ETHEREUM_ETH_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_ETH_ON_BFC_MAIN
    BRIDGED_BASE_ETH_ON_BIFROST = Asset.BRIDGED_BASE_MAIN_ETH_ON_BFC_MAIN
    UNIFIED_ETHEREUM_ETH_ON_BIFROST = Asset.UNIFIED_ETH_ON_BFC_MAIN

    # BNB---------------------------------------------------------------------------------------------------------------
    BNB_ON_BINANCE = Asset.BNB_ON_BNB_MAIN
    BRIDGED_BNB_ON_BIFROST = Asset.BRIDGED_BNB_MAIN_BNB_ON_BFC_MAIN
    UNIFIED_BNB_ON_BIFROST = Asset.UNIFIED_BNB_ON_BFC_MAIN

    # MATIC-------------------------------------------------------------------------------------------------------------
    MATIC_ON_POLYGON = Asset.MATIC_ON_MATIC_MAIN
    BRIDGED_MATIC_ON_BIFROST = Asset.BRIDGED_MATIC_MAIN_MATIC_ON_BFC_MAIN
    UNIFIED_MATIC_ON_BIFROST = Asset.UNIFIED_MATIC_ON_BFC_MAIN

    # USDC
    # ------------------------------------------------------------------------------------------------------------------
    USDC_ON_ETHEREUM = Asset.USDC_ON_ETH_MAIN
    USDC_ON_BINANCE = Asset.USDC_ON_BNB_MAIN

    BRIDGED_ETHEREUM_USDC_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_USDC_ON_BFC_MAIN
    BRIDGED_BINANCE_USDC_ON_BIFROST = Asset.BRIDGED_BNB_MAIN_USDC_ON_BFC_MAIN
    UNIFIED_USDC_ON_BIFROST = Asset.UNIFIED_USDC_ON_BFC_MAIN

    # USDT--------------------------------------------------------------------------------------------------------------
    USDT_ON_ETHEREUM = Asset.USDT_ON_ETH_MAIN
    BRIDGED_ETHEREUM_USDT_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_USDT_ON_BFC_MAIN
    UNIFIED_USDT_ON_BIFROST = Asset.UNIFIED_USDT_ON_BFC_MAIN

    # EGG---------------------------------------------------------------------------------------------------------------
    BRIDGED_ETHEREUM_EGG_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_EGG_ON_BFC_MAIN
    UNIFIED_EGG_ON_BIFROST = Asset.UNIFIED_EGG_ON_BFC_MAIN

    # WITCH-------------------------------------------------------------------------------------------------------------
    BRIDGED_ETHEREUM_WITCH_ON_BIFROST = Asset.BRIDGED_ETH_MAIN_WITCH_ON_BFC_MAIN
    UNIFIED_WITCH_ON_BIFROST = Asset.UNIFIED_WITCH_ON_BFC_MAIN

    # DAI---------------------------------------------------------------------------------------------------------------
    DAI_ON_BASE = Asset.DAI_ON_BASE_MAIN
    BRIDGED_BASE_DAI_ON_BIFROST = Asset.BRIDGED_BASE_MAIN_DAI_ON_BFC_MAIN
    UNIFIED_DAI_ON_BIFROST = Asset.UNIFIED_DAI_ON_BFC_MAIN

    def __init__(self, test_flag: bool):
        if test_flag:
            self.switch_testnet_config()

    @classmethod
    def from_bytes(cls, value: bytes):
        return Asset.from_bytes(value)

    @classmethod
    def from_name(cls, name):
        return Asset.from_name(name)

    @classmethod
    def size(cls) -> int:
        return Asset.size()

    def switch_testnet_config(self):
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
        self.BRIDGED_BASE_ETH_ON_BIFROST = Asset.BRIDGED_BASE_GOERLI_ETH_ON_BFC_TEST
        self.UNIFIED_ETHEREUM_ETH_ON_BIFROST = Asset.UNIFIED_ETH_ON_BFC_TEST

        # BNB---------------------------------------------------------------------------------------------------------------
        self.BNB_ON_BINANCE = Asset.BNB_ON_BNB_TEST
        self.BRIDGED_BNB_ON_BIFROST = Asset.BRIDGED_BNB_TEST_BNB_ON_BFC_TEST
        self.UNIFIED_BNB_ON_BIFROST = Asset.UNIFIED_BNB_ON_BFC_TEST

        # MATIC-------------------------------------------------------------------------------------------------------------
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

        # USDT--------------------------------------------------------------------------------------------------------------
        self.USDT_ON_ETHEREUM = Asset.USDT_ON_ETH_GOERLI
        self.BRIDGED_ETHEREUM_USDT_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_USDT_ON_BFC_TEST
        self.UNIFIED_USDT_ON_BIFROST = Asset.UNIFIED_USDT_ON_BFC_TEST

        # EGG---------------------------------------------------------------------------------------------------------------
        self.BRIDGED_ETHEREUM_EGG_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_EGG_ON_BFC_TEST
        self.UNIFIED_EGG_ON_BIFROST = Asset.UNIFIED_EGG_ON_BFC_TEST

        # WITCH-------------------------------------------------------------------------------------------------------------
        self.BRIDGED_ETHEREUM_WITCH_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_WITCH_ON_BFC_TEST
        self.UNIFIED_WITCH_ON_BIFROST = Asset.UNIFIED_WITCH_ON_BFC_TEST

        # DAI---------------------------------------------------------------------------------------------------------------
        self.DAI_ON_BASE = Asset.DAI_ON_BASE_GOERLI
        self.BRIDGED_BASE_DAI_ON_BIFROST = Asset.BRIDGED_BASE_GOERLI_DAI_ON_BFC_TEST
        self.UNIFIED_DAI_ON_BIFROST = Asset.UNIFIED_DAI_ON_BFC_TEST


asset_enum = AssetPrimitivesFactory('--testnet' in sys.argv[1:] or '-t' in sys.argv[1:])