import json
import unittest
from ..chainpy.eth.ethtype.consts import ChainIndex, EnumInterface, concat_2enum_as_int
from ..chainpy.eth.ethtype.hexbytes import EthHexBytes
from ..chainpy.eth.ethtype.utils import ETH_HASH


class TokenIndex(EnumInterface):
    BFC  = 0x0000000000000001
    BTC  = 0x0000000000000002
    ETH  = 0x0000000000000003
    DAI  = 0x0000000000000004
    USDC = 0x0000000000000005
    USDT = 0x0000000000000006
    LINK = 0x0000000000000007
    KLAY = 0x0000000000000008
    BUSD = 0x0000000000000009
    BNB = 0x000000000000000a
    MATIC = 0x000000000000000b
    BIFI = 0x000000000000000c
    WBFC = 0x000000000000000d
    AVAX = 0x000000000000000e

    @staticmethod
    def size():
        return 8


class TokenStreamIndex(EnumInterface):
    NONE             = 0x00000000000000000000000000000000

    # tokens relate to the Bifrost coin
    BFC_BIFROST      = concat_2enum_as_int(TokenIndex.BFC, ChainIndex.BIFROST)
    WBFC_BIFROST     = concat_2enum_as_int(TokenIndex.WBFC, ChainIndex.BIFROST)

    # bitcoin
    BTC_BITCOIN      = concat_2enum_as_int(TokenIndex.BTC, ChainIndex.BITCOIN)

    # tokens on the ethereum
    ETH_ETHEREUM     = concat_2enum_as_int(TokenIndex.ETH, ChainIndex.ETHEREUM)
    DAI_ETHEREUM     = concat_2enum_as_int(TokenIndex.DAI, ChainIndex.ETHEREUM)
    USDC_ETHEREUM    = concat_2enum_as_int(TokenIndex.USDC, ChainIndex.ETHEREUM)
    USDT_ETHEREUM    = concat_2enum_as_int(TokenIndex.USDT, ChainIndex.ETHEREUM)
    LINK_ETHEREUM    = concat_2enum_as_int(TokenIndex.LINK, ChainIndex.ETHEREUM)
    BIFI_ETHEREUM = concat_2enum_as_int(TokenIndex.BIFI, ChainIndex.ETHEREUM)

    BNB_BINANCE = concat_2enum_as_int(TokenIndex.BNB, ChainIndex.BINANCE)
    BUSD_BINANCE = concat_2enum_as_int(TokenIndex.BUSD, ChainIndex.BINANCE)

    MATIC_POLYGON = concat_2enum_as_int(TokenIndex.MATIC, ChainIndex.POLYGON)

    # tokens on the klaytn
    KLAY_KLAYTN      = concat_2enum_as_int(TokenIndex.KLAY, ChainIndex.KLAYTN)

    AVAX_AVALANCHE = concat_2enum_as_int(TokenIndex.AVAX, ChainIndex.AVALANCHE)

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def size() -> int:
        return TokenIndex.size() + ChainIndex.size()  # 16

    def home_chain_index(self) -> ChainIndex:
        value_bytes = EthHexBytes(self.value, self.size())
        return ChainIndex(value_bytes[TokenIndex.size():])

    def token_name(self) -> str:
        return self.name.split("_")[0]

    def is_coin_on(self, chain_index: ChainIndex) -> bool:
        home_chain = self.home_chain_index()  # BIFROST
        if chain_index != home_chain:
            return False

        if home_chain == ChainIndex.BIFROST:
            return self == TokenStreamIndex.BFC_BIFROST
        if home_chain == ChainIndex.ETHEREUM:
            return self == TokenStreamIndex.ETH_ETHEREUM
        if home_chain == ChainIndex.BINANCE:
            return self == TokenStreamIndex.BNB_BINANCE
        if home_chain == ChainIndex.POLYGON:
            return self == TokenStreamIndex.MATIC_POLYGON
        if home_chain == ChainIndex.KLAYTN:
            return self == TokenStreamIndex.KLAY_KLAYTN
        if home_chain == ChainIndex.AVALANCHE:
            return self == TokenStreamIndex.AVAX_AVALANCHE
        raise Exception("Not supported chain: {}".format(home_chain))


class RBCMethodIndex(EnumInterface):
    NONE = 0x000000
    WARP = 0x010001

    DEPOSIT = 0x020002
    REPAY = 0x020003
    WARP_SWAP = 0x020004
    XOPEN = 0x020005
    CALL = 0x020006

    WITHDRAW = 0x030007
    BORROW = 0x030008
    SWAP_WARP = 0x030009
    XEND = 0x03000a

    # CALL      = 0x03000b

    @staticmethod
    def size() -> int:
        return 8


class AggOracleId(EnumInterface):
    NONE = 0

    BFC_PRICE = TokenIndex.BFC.value
    BTC_PRICE = TokenIndex.BTC.value
    ETH_PRICE = TokenIndex.ETH.value
    DAI_PRICE = TokenIndex.DAI.value
    USDC_PRICE = TokenIndex.USDC.value
    USDT_PRICE = TokenIndex.USDT.value
    LINK_PRICE = TokenIndex.LINK.value
    KLAY_PRICE = TokenIndex.KLAY.value
    BNB_PRICE = TokenIndex.BNB.value
    MATIC_PRICE = TokenIndex.MATIC.value
    BIFI_PRICE = TokenIndex.BIFI.value
    BUSD_PRICE = TokenIndex.BUSD.value

    @staticmethod
    def size() -> int:
        return 32

    @classmethod
    def from_token_name(cls, token_name: str):
        return AggOracleId[token_name + "_PRICE"]


class ConsensusOracleId(EnumInterface):
    NONE = 0

    BTC_HASH = int(ETH_HASH("bitcoinblockhash".encode()).hexdigest(), 16)

    @staticmethod
    def size() -> int:
        return 32


class ChainEventStatus(EnumInterface):
    NONE = 0
    REQUESTED = 1
    FAILED = 2
    EXECUTED = 3
    REVERTED = 4
    ACCEPTED = 5
    REJECTED = 6
    COMMITTED = 7
    ROLLBACKED = 8
    NEXT_AUTHORITY_RELAYED = 9
    NEXT_AUTHORITY_COMMITTED = 10

    @staticmethod
    def size():
        return 1


class TestEnum(unittest.TestCase):

    @staticmethod
    def generate_dict_for_index(index_type):
        index_dict = {"bsize": index_type.size()}
        for idx in index_type:
            index_dict[idx.name] = idx.formatted_hex()
        return index_dict

    def test_print_enum(self):
        enum_dict = {}
        enum_dict["ChainIndex"] = TestEnum.generate_dict_for_index(ChainIndex)
        enum_dict["TokenIndex"] = TestEnum.generate_dict_for_index(TokenIndex)

        enum_dict["TokenStreamIndex"] = TestEnum.generate_dict_for_index(TokenStreamIndex)
        enum_dict["ChainEventStatus"] = TestEnum.generate_dict_for_index(ChainEventStatus)
        enum_dict["RBCMethodIndex"] = TestEnum.generate_dict_for_index(RBCMethodIndex)
        enum_dict["AggOracleId"] = TestEnum.generate_dict_for_index(AggOracleId)
        enum_dict["ConsensusOracleId"] = TestEnum.generate_dict_for_index(ConsensusOracleId)

        print(json.dumps(enum_dict, indent=4))
