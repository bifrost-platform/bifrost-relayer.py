from enum import Enum
from typing import cast, List, Union

from rbclib.primitives.chain import ChainEnum, MainnetPrimitives, TestnetPrimitives
from rbclib.primitives.symbol import Symbol
from rbclib.utils import concat_as_int, parser

ERC20_ADDRESS_BSIZE = 20
COIN_ADDRESS = "0x" + "ff" * 20


class AssetType(Enum):
    NONE = 0
    COIN = 1
    UNIFIED = 2
    BRIDGED = 3
    RESERVED = 0xffffffff

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name

    @classmethod
    def size(cls) -> int:
        return 4

    @classmethod
    def str_with_size(cls):
        return cls.__name__ + "-{}".format(cls.size())


class Asset(Enum):
    NONE = 0

    # # BTC
    # # ----------------------------------------------------------------------------------------------------------------
    # BTC_ON_BTC_MAIN = concat_as_int(
    #     Symbol.BTC, Chain.BTC_MAIN, COIN_ADDRESS
    # )
    # BTC_ON_BTC_TEST = concat_as_int(
    #     Symbol.BTC, Chain.BTC_TEST, COIN_ADDRESS
    # )
    # # ----------------------------------------------------------------------------------------------------------------
    # BTC_ON_ETH_MAIN = concat_as_int(
    #     Symbol.BTC, MainnetPrimitives.ETHEREUM, 0
    # )
    # BTC_ON_ETH_GOERLI = concat_as_int(
    #     Symbol.BTC, TestnetPrimitives.ETHEREUM, 0
    # )
    # # ----------------------------------------------------------------------------------------------------------------
    # BRIDGED_BTC_MAIN_BTC_ON_BFC_MAIN = concat_as_int(
    #     Symbol.BTC, MainnetPrimitives.BIFROST, 0
    # )
    # BRIDGED_BTC_MAIN_BTC_ON_BFC_TEST = concat_as_int(
    #     Symbol.BTC, TestnetPrimitives.BIFROST, 0
    # )
    # BRIDGED_BTC_TEST_BTC_ON_BFC_MAIN = concat_as_int(
    #     Symbol.BTC, MainnetPrimitives.BIFROST, 0
    # )
    # BRIDGED_BTC_TEST_BTC_ON_BFC_TEST = concat_as_int(
    #     Symbol.BTC, TestnetPrimitives.BIFROST, 0
    # )
    # UNIFIED_BTC_ON_BFC_MAIN = concat_as_int(
    #     Symbol.BTC, MainnetPrimitives.BIFROST, 0
    # )
    # UNIFIED_BTC_ON_BFC_TEST = concat_as_int(
    #     Symbol.BTC, TestnetPrimitives.BIFROST, 0
    # )
    # # ----------------------------------------------------------------------------------------------------------------

    # BFC
    # ------------------------------------------------------------------------------------------------------------------
    BFC_ON_BFC_MAIN = concat_as_int(Symbol.BFC, AssetType.COIN, MainnetPrimitives.BIFROST, COIN_ADDRESS)
    BFC_ON_BFC_TEST = concat_as_int(Symbol.BFC, AssetType.COIN, TestnetPrimitives.BIFROST, COIN_ADDRESS)
    # ------------------------------------------------------------------------------------------------------------------
    BFC_ON_ETH_MAIN = concat_as_int(
        Symbol.BFC, AssetType.RESERVED, MainnetPrimitives.ETHEREUM, "0x0c7D5ae016f806603CB1782bEa29AC69471CAb9c"
    )
    BFC_ON_ETH_GOERLI = concat_as_int(
        Symbol.BFC, AssetType.RESERVED, TestnetPrimitives.ETHEREUM, "0x3A815eBa66EaBE966a6Ae7e5Df9652eca24e9c54"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_ETH_MAIN_BFC_ON_BFC_MAIN = concat_as_int(
        Symbol.BFC, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0xEEDAb47DFBC7564CD8EB314bdA33405Ac9852326"
    )
    BRIDGED_ETH_GOERLI_BFC_ON_BFC_TEST = concat_as_int(
        Symbol.BFC, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xfB5D65B8e8784ae3e004e1e476B05d408e6A1f2D"
    )
    UNIFIED_BFC_ON_BFC_MAIN = concat_as_int(
        Symbol.BFC, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0xAe172D8c5E428D4b7C70f9E593b207F9daC9BF3e"
    )
    UNIFIED_BFC_ON_BFC_TEST = concat_as_int(
        Symbol.BFC, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0xB0fF18CB2d0F3f51a9c54Af862ed98f3caa027A1"
    )
    # ------------------------------------------------------------------------------------------------------------------

    # BIFI
    # ------------------------------------------------------------------------------------------------------------------
    BIFI_ON_ETH_MAIN = concat_as_int(
        Symbol.BIFI, AssetType.RESERVED, MainnetPrimitives.ETHEREUM, "0x2791BfD60D232150Bff86b39B7146c0eaAA2BA81"
    )
    BIFI_ON_ETH_GOERLI = concat_as_int(
        Symbol.BIFI, AssetType.RESERVED, TestnetPrimitives.ETHEREUM, "0x055ED934c426855caB467FdF8441D4FD6a7D2659"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_ETH_MAIN_BIFI_ON_BFC_MAIN = concat_as_int(
        Symbol.BIFI, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x4C7a44F3FB37A53F33D3fe3cCdE97A444F105239"
    )
    BRIDGED_ETH_GOERLI_BIFI_ON_BFC_TEST = concat_as_int(
        Symbol.BIFI, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xC4F1CcafCBeB0BE0F1CDBA499696603528655F29"
    )
    UNIFIED_BIFI_ON_BFC_MAIN = concat_as_int(
        Symbol.BIFI, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0x047938C3aD13c1eB821C8e310B2B6F889b6d0003"
    )
    UNIFIED_BIFI_ON_BFC_TEST = concat_as_int(
        Symbol.BIFI, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0x8010a873d59719e895E20f15f9906B5a1F399C3A")
    # ------------------------------------------------------------------------------------------------------------------

    # ETH
    # ------------------------------------------------------------------------------------------------------------------
    ETH_ON_ETH_MAIN = concat_as_int(Symbol.ETH, AssetType.COIN, MainnetPrimitives.ETHEREUM, COIN_ADDRESS)
    ETH_ON_ETH_GOERLI = concat_as_int(Symbol.ETH, AssetType.COIN, TestnetPrimitives.ETHEREUM, COIN_ADDRESS)

    ETH_ON_BASE_MAIN = concat_as_int(Symbol.ETH, AssetType.COIN, MainnetPrimitives.BASE, COIN_ADDRESS)
    ETH_ON_BASE_GOERLI = concat_as_int(Symbol.ETH, AssetType.COIN, TestnetPrimitives.BASE, COIN_ADDRESS)
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_ETH_MAIN_ETH_ON_BFC_MAIN = concat_as_int(
        Symbol.ETH, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x98e266BDb0eedd38BF45232B9316959ad0Aad90c"
    )
    BRIDGED_ETH_GOERLI_ETH_ON_BFC_TEST = concat_as_int(
        Symbol.ETH, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xD089773D293F43440529e6cfa84639E0498A0277"
    )
    UNIFIED_ETH_ON_BFC_MAIN = concat_as_int(
        Symbol.ETH, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0x6c9944674C1D2cF6c4c4999FC7290Ba105dcd70e"
    )
    UNIFIED_ETH_ON_BFC_TEST = concat_as_int(
        Symbol.ETH, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0xc83EEd1bf5464eD5383bc3342b918E08f6815950"
    )

    BRIDGED_BASE_MAIN_ETH_ON_BFC_MAIN = concat_as_int(
        Symbol.ETH, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x2b864bb73CeE4b1867CCe9944678dBEfEdaF2517"
    )
    BRIDGED_BASE_GOERLI_ETH_ON_BFC_TEST = concat_as_int(
        Symbol.ETH, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xf86fd65bA36Dca61892e3e6a41b40BEAb9171d00"
    )
    # ------------------------------------------------------------------------------------------------------------------

    # BNB
    # ------------------------------------------------------------------------------------------------------------------
    BNB_ON_BNB_MAIN = concat_as_int(Symbol.BNB, AssetType.COIN, MainnetPrimitives.BINANCE, COIN_ADDRESS)
    BNB_ON_BNB_TEST = concat_as_int(Symbol.BNB, AssetType.COIN, TestnetPrimitives.BINANCE, COIN_ADDRESS)
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_BNB_MAIN_BNB_ON_BFC_MAIN = concat_as_int(
        Symbol.BNB, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x872b347cd764d46c127ffefbcaB605FFF3f3a48C"
    )
    BRIDGED_BNB_TEST_BNB_ON_BFC_TEST = concat_as_int(
        Symbol.BNB, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0x72D22DF54b86d25D9F9E0C10D516Ab22517b7051"
    )
    UNIFIED_BNB_ON_BFC_MAIN = concat_as_int(
        Symbol.BNB, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0xB800EaF843F962DFe5e145A8c9D07A3e70b11d7F"
    )
    UNIFIED_BNB_ON_BFC_TEST = concat_as_int(
        Symbol.BNB, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0xCd8bf79fA84D551f2465C0a646cABc295d43Be5C"
    )
    # ------------------------------------------------------------------------------------------------------------------

    # AVAX
    # # ----------------------------------------------------------------------------------------------------------------
    # AVAX_ON_AVAX_MAIN = concat_as_int(Symbol.AVAX, AssetType.COIN, Chain.AVAX_MAIN, COIN_ADDRESS)
    # AVAX_ON_AVAX_FUJI = concat_as_int(Symbol.AVAX, AssetType.COIN, Chain.AVAX_FUJI, COIN_ADDRESS)
    # # ----------------------------------------------------------------------------------------------------------------
    # BRIDGE_AVAX_MAIN_AVAX_ON_BFC_MAIN = concat_as_int(Symbol.AVAX, AssetType.BRIDGED, MainnetPrimitives.BIFROST, 48)
    # BRIDGE_AVAX_MAIN_AVAX_ON_BFC_TEST = concat_as_int(Symbol.AVAX, AssetType.BRIDGED, TestnetPrimitives.BIFROST, 49)
    # BRIDGE_AVAX_FUJI_AVAX_ON_BFC_MAIN = concat_as_int(Symbol.AVAX, AssetType.BRIDGED, MainnetPrimitives.BIFROST, 50)
    # BRIDGE_AVAX_FUJI_AVAX_ON_BFC_TEST = concat_as_int(Symbol.AVAX, AssetType.BRIDGED, TestnetPrimitives.BIFROST, 51)
    # UNIFIED_AVAX_ON_BFC_MAIN = concat_as_int(Symbol.AVAX, AssetType.UNIFIED, MainnetPrimitives.BIFROST, 52)
    # UNIFIED_AVAX_ON_BFC_TEST = concat_as_int(Symbol.AVAX, AssetType.UNIFIED, TestnetPrimitives.BIFROST, 53)
    # # ----------------------------------------------------------------------------------------------------------------
    #
    # MATIC
    # ----------------------------------------------------------------------------------------------------------------
    MATIC_ON_MATIC_MAIN = concat_as_int(Symbol.MATIC, AssetType.COIN, MainnetPrimitives.MATIC, COIN_ADDRESS)
    MATIC_ON_MATIC_MUMBAI = concat_as_int(Symbol.MATIC, AssetType.COIN, TestnetPrimitives.MATIC, COIN_ADDRESS)
    # ----------------------------------------------------------------------------------------------------------------
    BRIDGED_MATIC_MAIN_MATIC_ON_BFC_MAIN = concat_as_int(
        Symbol.MATIC, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0xf549E4B5B4Cb7fd4e83b8AA047C742C06D527429"
    )
    BRIDGED_MATIC_MUMBAI_MATIC_ON_BFC_TEST = concat_as_int(
        Symbol.MATIC, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0x82c1aD3aF709210F203869a03CdE8C7d0b9841d8"
    )
    UNIFIED_MATIC_ON_BFC_MAIN = concat_as_int(
        Symbol.MATIC, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0x21ad243b81eff53482F6F6E7C76539f2CfC0B734"
    )
    UNIFIED_MATIC_ON_BFC_TEST = concat_as_int(
        Symbol.MATIC, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0xad115F901a1Af99dc83D055C89641031fd1a50Dc"
    )
    # ----------------------------------------------------------------------------------------------------------------

    # USDC
    # ------------------------------------------------------------------------------------------------------------------
    USDC_ON_ETH_MAIN = concat_as_int(
        Symbol.USDC, AssetType.RESERVED, MainnetPrimitives.ETHEREUM, "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    )
    USDC_ON_ETH_GOERLI = concat_as_int(
        Symbol.USDC, AssetType.RESERVED, TestnetPrimitives.ETHEREUM, "0xD978Be30CE95D42DF7067b988f25bCa2b286Fb70"
    )
    USDC_ON_BNB_MAIN = concat_as_int(
        Symbol.USDC, AssetType.RESERVED, MainnetPrimitives.BINANCE, "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
    )
    USDC_ON_BNB_TEST = concat_as_int(
        Symbol.USDC, AssetType.RESERVED, TestnetPrimitives.BINANCE, "0xC9C0aD3179eE2f4801454926ED5D6A2Da30b56FB"
    )
    USDC_ON_MATIC_MAIN = concat_as_int(
        Symbol.USDC, AssetType.RESERVED, MainnetPrimitives.MATIC, "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    )
    USDC_ON_MATIC_MUMBAI = concat_as_int(
        Symbol.USDC, AssetType.RESERVED, TestnetPrimitives.MATIC, "0xc508ab50142721A0213A47AaFF4E93C3eDb978E2"
    )

    # USDC_ON_AVAX_MAIN = concat_as_int(Symbol.USDC, AssetType.RESERVED, Chain.AVAX_MAIN, 64)
    # USDC_ON_AVAX_FUJI = concat_as_int(Symbol.USDC, AssetType.RESERVED, Chain.AVAX_FUJI, 64)
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_ETH_MAIN_USDC_ON_BFC_MAIN = concat_as_int(
        Symbol.USDC, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0xac1552e30857A814a225BAa81145bcB071B46DDd"
    )
    BRIDGED_ETH_GOERLI_USDC_ON_BFC_TEST = concat_as_int(
        Symbol.USDC, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xa7bb0a2693fb4d1ab9a6C5acCf5C63f12fab1855"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_BNB_MAIN_USDC_ON_BFC_MAIN = concat_as_int(
        Symbol.USDC, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x4F7aB59b5AC112970F5dD66D8a7ac505c8E5e08B"
    )
    BRIDGED_BNB_TEST_USDC_ON_BFC_TEST = concat_as_int(
        Symbol.USDC, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xC67f0b7c01f6888D43B563B3a8B851856BcfAB64"
    )
    BRIDGED_MATIC_MAIN_USDC_ON_BFC_MAIN = concat_as_int(
        Symbol.USDC, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x7E3A761afceC9f3E2fb7E853fFc45a62319143fA"
    )
    BRIDGED_MATIC_MUMBAI_USDC_ON_BFC_TEST = concat_as_int(
        Symbol.USDC, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0x6442Fdd287E04e68f0C6f40b4a8e5a375d16482C"
    )

    # # ----------------------------------------------------------------------------------------------------------------
    # BRIDGED_MATIC_MAIN_USDC_ON_BFC_TEST = concat_as_int(Symbol.USDC, AssetType.BRIDGED, TestnetPrimitives.BIFROST, 81)
    # BRIDGED_MATIC_MUMBAI_USDC_ON_BFC_MAIN = concat_as_int(Symbol.USDC, AssetType.BRIDGED, MainnetPrimitives.BIFROST, 82)
    # # ----------------------------------------------------------------------------------------------------------------
    # BRIDGED_AVAX_MAIN_USDC_ON_BFC_MAIN = concat_as_int(Symbol.USDC, AssetType.BRIDGED, MainnetPrimitives.BIFROST, 88)
    # BRIDGED_AVAX_MAIN_USDC_ON_BFC_TEST = concat_as_int(Symbol.USDC, AssetType.BRIDGED, TestnetPrimitives.BIFROST, 89)
    # BRIDGED_AVAX_FUJI_USDC_ON_BFC_MAIN = concat_as_int(Symbol.USDC, AssetType.BRIDGED, MainnetPrimitives.BIFROST, 91)
    # BRIDGED_AVAX_FUJI_USDC_ON_BFC_TEST = concat_as_int(Symbol.USDC, AssetType.BRIDGED, TestnetPrimitives.BIFROST, 92)
    # # ----------------------------------------------------------------------------------------------------------------
    UNIFIED_USDC_ON_BFC_MAIN = concat_as_int(
        Symbol.USDC, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0x640952E7984f2ECedeAd8Fd97aA618Ab1210A21C"
    )
    UNIFIED_USDC_ON_BFC_TEST = concat_as_int(
        Symbol.USDC, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0x28661511CDA7119B2185c647F23106a637CC074f"
    )
    # ------------------------------------------------------------------------------------------------------------------

    # USDT
    # ------------------------------------------------------------------------------------------------------------------
    USDT_ON_ETH_MAIN = concat_as_int(
        Symbol.USDT, AssetType.RESERVED, MainnetPrimitives.ETHEREUM, "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    )
    USDT_ON_ETH_GOERLI = concat_as_int(
        Symbol.USDT, AssetType.RESERVED, TestnetPrimitives.ETHEREUM, "0xF26d15E6484e00Af2772b840eb4F2B36F0BD569C"
    )
    USDT_ON_MATIC_MAIN = concat_as_int(
        Symbol.USDT, AssetType.RESERVED, MainnetPrimitives.MATIC, "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
    )
    USDT_ON_MATIC_MUMBAI = concat_as_int(
        Symbol.USDT, AssetType.RESERVED, TestnetPrimitives.MATIC, "0x312d92B462492B2D110c7b378a72F6F78B1d6289"
    )
    USDT_ON_BNB_MAIN = concat_as_int(
        Symbol.USDT, AssetType.RESERVED, MainnetPrimitives.BINANCE, "0x55d398326f99059fF775485246999027B3197955"
    )
    USDT_ON_BNB_TEST = concat_as_int(
        Symbol.USDT, AssetType.RESERVED, TestnetPrimitives.BINANCE, "0x66B57c5ea363cFC94033275675C57776F89B06C4"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_ETH_MAIN_USDT_ON_BFC_MAIN = concat_as_int(
        Symbol.USDT, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x228F3875392CFb0Ad0e4aF2E95A050EdbCc8668B"
    )
    BRIDGED_ETH_GOERLI_USDT_ON_BFC_TEST = concat_as_int(
        Symbol.USDT, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0x43585F3De72c712e0a2DbC6a24Dd6d9A962B6e90"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_BNB_MAIN_USDT_ON_BFC_MAIN = concat_as_int(
        Symbol.USDT, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x00000000000000000000000000000000000000b0"
    )
    BRIDGED_BNB_TEST_USDT_ON_BFC_TEST = concat_as_int(
        Symbol.USDT, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xe2baDe8Ff7ce0ABcF5952ecc79A1212e7B6C496E"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_MATIC_MAIN_USDT_ON_BFC_MAIN = concat_as_int(
        Symbol.USDT, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x00000000000000000000000000000000000000c0"
    )
    BRIDGED_MATIC_MUMBAI_USDT_ON_BFC_TEST = concat_as_int(
        Symbol.USDT, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xC3C12EF3BC5A8914eB3f4C190358ce5A41B19b46"
    )
    UNIFIED_USDT_ON_BFC_MAIN = concat_as_int(
        Symbol.USDT, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0x3eA8654d5755e673599473ab37d92788B5bA12aE"
    )
    UNIFIED_USDT_ON_BFC_TEST = concat_as_int(
        Symbol.USDT, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0x815e850CDDb2BB8C8afb61266525daFfB9adD7dc"
    )

    # SAT
    # ------------------------------------------------------------------------------------------------------------------
    SAT_ON_ETH_MAIN = concat_as_int(
        Symbol.SAT, AssetType.RESERVED, MainnetPrimitives.ETHEREUM, "0x5abf88cf3444611d13f6d1b39f3f3ee8575c91a2"
    )
    SAT_ON_ETH_GOERLI = concat_as_int(
        Symbol.SAT, AssetType.RESERVED, TestnetPrimitives.ETHEREUM, "0x4a5FC8893Db2Fa06ebe3D7Ec21a1d9466ee54442"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_ETH_MAIN_SAT_ON_BFC_MAIN = concat_as_int(
        Symbol.SAT, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0xAD01dE2A0413B764F16643dBdc1667adc6D88FE9"
    )
    BRIDGED_ETH_GOERLI_SAT_ON_BFC_TEST = concat_as_int(
        Symbol.SAT, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xd2Ae6529057BE0b4Ef44bB4A127ee76B1c2863CB"
    )
    UNIFIED_SAT_ON_BFC_MAIN = concat_as_int(
        Symbol.SAT, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0x17102AC78a02a98fC78B0c29B7b0506f035A99E5"
    )
    UNIFIED_SAT_ON_BFC_TEST = concat_as_int(
        Symbol.SAT, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0x3325B631CD1B972628f021c3bB776e21290baB21"
    )
    # ----------------------------------------------------------------------------------------------------------------

    # WITCH
    # ------------------------------------------------------------------------------------------------------------------
    WITCH_ON_ETH_MAIN = concat_as_int(
        Symbol.WITCH, AssetType.RESERVED, MainnetPrimitives.ETHEREUM, "0xdc524e3c6910257744C1F93Cf15E9F472b5bD236"
    )
    WITCH_ON_ETH_GOERLI = concat_as_int(
        Symbol.WITCH, AssetType.RESERVED, TestnetPrimitives.ETHEREUM, "0x8d9a156587C4593F34294D6b1DCBc7A5F29e0356"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_ETH_MAIN_WITCH_ON_BFC_MAIN = concat_as_int(
        Symbol.WITCH, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0xA041E39E010B9B1B2483074a28F88c2ABA1F5a8c"
    )
    BRIDGED_ETH_GOERLI_WITCH_ON_BFC_TEST = concat_as_int(
        Symbol.WITCH, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0xb8fFfC7111FCCC3ceBeE680c5221bB5E6f9F5935"
    )
    UNIFIED_WITCH_ON_BFC_MAIN = concat_as_int(
        Symbol.WITCH, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0xB1f3A83597Bce2AD842c29bD750AE17afc474137"
    )
    UNIFIED_WITCH_ON_BFC_TEST = concat_as_int(
        Symbol.WITCH, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0x97C46701A8599DF99abB306ce8980B5f57D833fB"
    )
    # ----------------------------------------------------------------------------------------------------------------

    # P2D
    # ------------------------------------------------------------------------------------------------------------------
    P2D_ON_BNB_MAIN = concat_as_int(
        Symbol.P2D, AssetType.RESERVED, MainnetPrimitives.BINANCE, "0x3ce414000C518FC55846388ef0aaB5d0abf275Be"
    )
    P2D_ON_BNB_TEST = concat_as_int(
        Symbol.P2D, AssetType.RESERVED, TestnetPrimitives.BINANCE, "0x018185EB57D6DA77A269EC740e80EF6eBEE793EC"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_BNB_MAIN_P2D_ON_BFC_MAIN = concat_as_int(
        Symbol.P2D, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x8bf78DAa2f98758ac116acdb64e9E9979a697d81"
    )
    BRIDGED_BNB_TEST_P2D_ON_BFC_TEST = concat_as_int(
        Symbol.P2D, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0x90848FD52d615f733dCdA8290e9a96152148413e"
    )
    UNIFIED_P2D_ON_BFC_MAIN = concat_as_int(
        Symbol.P2D, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0xAa2E0911AC56C6f8A9C4f0006A8C907D5d180A6a"
    )
    UNIFIED_P2D_ON_BFC_TEST = concat_as_int(
        Symbol.P2D, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0xDa007Bea12013Ee90D5DEC4111DBA5bd98314F93"
    )
    # ----------------------------------------------------------------------------------------------------------------

    # EGG
    # ------------------------------------------------------------------------------------------------------------------
    EGG_ON_ETH_MAIN = concat_as_int(
        Symbol.EGG, AssetType.RESERVED, MainnetPrimitives.ETHEREUM, "0x65ccd72c0813ce6f2703593b633202a0f3ca6a0c"
    )
    EGG_ON_ETH_GOERLI = concat_as_int(
        Symbol.EGG, AssetType.RESERVED, TestnetPrimitives.ETHEREUM, "0x9225c534403eEAB0B80394F60683F51EF9acD627"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_ETH_MAIN_EGG_ON_BFC_MAIN = concat_as_int(
        Symbol.EGG, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0xa24c671711DF240fD6967D655aD1Ef056675be01"
    )
    BRIDGED_ETH_GOERLI_EGG_ON_BFC_TEST = concat_as_int(
        Symbol.EGG, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0x2E4a76c993CAD19595049fAE0D747E51fa452300"
    )
    UNIFIED_EGG_ON_BFC_MAIN = concat_as_int(
        Symbol.EGG, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0x9DD4d64e41EA7Fc90ACEC15B08552172Ce94556a"
    )
    UNIFIED_EGG_ON_BFC_TEST = concat_as_int(
        Symbol.EGG, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0xc53CE1aA929e9E8B7F9587bbEE2aB0fB530Fe676"
    )
    # ----------------------------------------------------------------------------------------------------------------

    # DAI
    # ------------------------------------------------------------------------------------------------------------------
    DAI_ON_BASE_MAIN = concat_as_int(
        Symbol.DAI, AssetType.RESERVED, MainnetPrimitives.BASE, "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
    )
    DAI_ON_BASE_GOERLI = concat_as_int(
        Symbol.DAI, AssetType.RESERVED, TestnetPrimitives.BASE, "0x263deEAd49900486A1E9C312BB70CC172E333917"
    )
    # ------------------------------------------------------------------------------------------------------------------
    BRIDGED_BASE_MAIN_DAI_ON_BFC_MAIN = concat_as_int(
        Symbol.DAI, AssetType.BRIDGED, MainnetPrimitives.BIFROST, "0x99a286cd4eD4BCDEfC179b39242B4Ce5f82A9F7C"
    )
    BRIDGED_BASE_GOERLI_DAI_ON_BFC_TEST = concat_as_int(
        Symbol.DAI, AssetType.BRIDGED, TestnetPrimitives.BIFROST, "0x0D83DaE4cadeBeBd6709068810CD2E4C0D761856"
    )
    UNIFIED_DAI_ON_BFC_MAIN = concat_as_int(
        Symbol.DAI, AssetType.UNIFIED, MainnetPrimitives.BIFROST, "0xcDB9579Db96EB5C8298dF889D915D0FF668AfF2a"
    )
    UNIFIED_DAI_ON_BFC_TEST = concat_as_int(
        Symbol.DAI, AssetType.UNIFIED, TestnetPrimitives.BIFROST, "0x2353859d0c5CD0CB4Da701d2aCA9f1222Ad71110"
    )

    # ----------------------------------------------------------------------------------------------------------------

    # # BUSD
    # # ----------------------------------------------------------------------------------------------------------------
    # BUSD_ON_BNB_MAIN = concat_as_int(Symbol.BUSD, AssetType.RESERVED, MainnetPrimitives.BINANCE, 97)
    # BUSD_ON_BNB_TEST = concat_as_int(Symbol.BUSD, AssetType.RESERVED, TestnetPrimitives.BINANCE, 98)
    # # ----------------------------------------------------------------------------------------------------------------
    # BRIDGED_BNB_MAIN_BUSD_ON_BFC_MAIN = concat_as_int(Symbol.BUSD, AssetType.BRIDGED, MainnetPrimitives.BIFROST, 99)
    # BRIDGED_BNB_MAIN_BUSD_ON_BFC_TEST = concat_as_int(Symbol.BUSD, AssetType.BRIDGED, TestnetPrimitives.BIFROST, 99)
    # BRIDGED_BNB_TEST_BUSD_ON_BFC_MAIN = concat_as_int(Symbol.BUSD, AssetType.BRIDGED, MainnetPrimitives.BIFROST, 100)
    # BRIDGED_BNB_TEST_BUSD_ON_BFC_TEST = concat_as_int(Symbol.BUSD, AssetType.BRIDGED, MainnetPrimitives.BIFROST, 101)
    # UNIFIED_BUSD_ON_BFC_MAIN = concat_as_int(Symbol.BUSD, AssetType.UNIFIED, MainnetPrimitives.BIFROST, 102)
    # UNIFIED_BUSD_ON_BFC_TEST = concat_as_int(Symbol.BUSD, AssetType.UNIFIED, TestnetPrimitives.BIFROST, 103)
    # # ----------------------------------------------------------------------------------------------------------------

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [Symbol.str_with_size(), AssetType.str_with_size(), ChainEnum.str_with_size(), "ADDRESS-{}".format(ERC20_ADDRESS_BSIZE)]

    @staticmethod
    def size():
        return Symbol.size() + AssetType.size() + ChainEnum.size() + ERC20_ADDRESS_BSIZE

    def analyze(self) -> List[Union[str, type]]:
        """ symbol, related chain and erc20 address """
        return parser(self.formatted_hex(), [Symbol, AssetType, ChainEnum, ERC20_ADDRESS_BSIZE])

    def formatted_bytes(self) -> bytes:
        return self.value.to_bytes(self.size(), "big")

    def formatted_hex(self) -> str:
        return "0x" + self.formatted_bytes().hex()

    def is_coin(self) -> bool:
        return self.asset_type == AssetType.COIN

    @property
    def symbol(self) -> Symbol:
        return cast(Symbol, self.analyze()[0])

    @property
    def asset_type(self) -> AssetType:
        return cast(AssetType, self.analyze()[1])

    @property
    def chain(self) -> ChainEnum:
        from typing import cast
        return cast(ChainEnum, self.analyze()[2])

    @property
    def address(self) -> str:
        from rbclib.utils import to_even_hex
        return to_even_hex(self.analyze()[3])

    @property
    def decimal(self) -> int:
        return self.symbol.decimal

    @classmethod
    def from_bytes(cls, value: bytes):
        len_op = int.from_bytes(value[:1], "big")
        return cls(int.from_bytes(value[:len_op + 1], "big"))
