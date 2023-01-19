from bridgeconst.consts import Chain, Asset


def switch_to_test_config():
    SwitchableChain.BIFROST = Chain.BFC_TEST
    SwitchableChain.ETHEREUM = Chain.ETH_GOERLI
    SwitchableChain.BINANCE = Chain.BNB_TEST
    SwitchableChain.MATIC = Chain.MATIC_MUMBAI
    SwitchableChain.AVALANCHE = Chain.AVAX_FUJI

    # BFC---------------------------------------------------------------------------------------------------------------
    SwitchableAsset.BFC_ON_BIFROST = Asset.BFC_ON_BFC_TEST
    SwitchableAsset.BFC_ON_ETHEREUM = Asset.BFC_ON_ETH_GOERLI
    SwitchableAsset.BRIDGED_ETHEREUM_BFC_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_BFC_ON_BFC_TEST
    SwitchableAsset.UNIFIED_BFC_ON_BIFROST = Asset.UNIFIED_BFC_ON_BFC_TEST

    # BIFI--------------------------------------------------------------------------------------------------------------
    SwitchableAsset.BIFI_ON_ETHEREUM = Asset.BIFI_ON_ETH_GOERLI
    SwitchableAsset.BRIDGED_ETHEREUM_BIFI_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_BIFI_ON_BFC_TEST
    SwitchableAsset.UNIFIED_BIFI_ON_BIFROST = Asset.UNIFIED_BIFI_ON_BFC_TEST

    # ETH---------------------------------------------------------------------------------------------------------------
    SwitchableAsset.ETH_ON_ETHEREUM = Asset.ETH_ON_ETH_GOERLI
    SwitchableAsset.BRIDGED_ETHEREUM_ETH_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_ETH_ON_BFC_TEST
    SwitchableAsset.UNIFIED_ETHEREUM_ETH_ON_BIFROST = Asset.UNIFIED_ETH_ON_BFC_TEST

    # BNB---------------------------------------------------------------------------------------------------------------
    SwitchableAsset.BNB_ON_BINANCE = Asset.BNB_ON_BNB_TEST
    SwitchableAsset.BRIDGED_BNB_ON_BIFROST = Asset.BRIDGED_BNB_TEST_BNB_ON_BFC_TEST
    SwitchableAsset.UNIFIED_BNB_ON_BIFROST = Asset.UNIFIED_BNB_ON_BFC_TEST

    # MATIC------------------------------------------------------------------------------------------------------------
    SwitchableAsset.MATIC_ON_POLYGON = Asset.MATIC_ON_MATIC_MUMBAI
    SwitchableAsset.BRIDGED_MATIC_ON_BIFROST = Asset.BRIDGED_MATIC_MUMBAI_MATIC_ON_BFC_TEST
    SwitchableAsset.UNIFIED_MATIC_ON_BIFROST = Asset.UNIFIED_MATIC_ON_BFC_TEST

    # USDC
    # ------------------------------------------------------------------------------------------------------------------
    SwitchableAsset.USDC_ON_ETHEREUM = Asset.USDC_ON_ETH_GOERLI
    SwitchableAsset.USDC_ON_BINANCE = Asset.USDC_ON_BNB_TEST

    SwitchableAsset.BRIDGED_ETHEREUM_USDC_ON_BIFROST = Asset.BRIDGED_ETH_GOERLI_USDC_ON_BFC_TEST
    SwitchableAsset.BRIDGED_BINANCE_USDC_ON_BIFROST = Asset.BRIDGED_BNB_TEST_USDC_ON_BFC_TEST
    SwitchableAsset.UNIFIED_USDC_ON_BIFROST = Asset.UNIFIED_USDC_ON_BFC_TEST


class SwitchableChain:
    NONE = Chain.NONE
    BIFROST = Chain.BFC_MAIN
    ETHEREUM = Chain.ETH_MAIN
    BINANCE = Chain.BNB_MAIN
    MATIC = Chain.MATIC_MAIN
    AVALANCHE = Chain.AVAX_MAIN

    @classmethod
    def from_bytes(cls, value: bytes):
        return Chain.from_bytes(value)

    @classmethod
    def from_name(cls, name):
        return Chain.from_name(name)

    @classmethod
    def size(cls) -> int:
        return Chain.size()


class SwitchableAsset:
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
    UNIFIED_ETHEREUM_ETH_ON_BIFROST = Asset.UNIFIED_ETH_ON_BFC_MAIN

    # BNB---------------------------------------------------------------------------------------------------------------
    BNB_ON_BINANCE = Asset.BNB_ON_BNB_MAIN
    BRIDGED_BNB_ON_BIFROST = Asset.BRIDGED_BNB_MAIN_BNB_ON_BFC_MAIN
    UNIFIED_BNB_ON_BIFROST = Asset.UNIFIED_BNB_ON_BFC_MAIN

    # MATIC------------------------------------------------------------------------------------------------------------
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

    @classmethod
    def from_bytes(cls, value: bytes):
        return Asset.from_bytes(value)

    @classmethod
    def from_name(cls, name):
        return Asset.from_name(name)

    @classmethod
    def size(cls) -> int:
        return Asset.size()
