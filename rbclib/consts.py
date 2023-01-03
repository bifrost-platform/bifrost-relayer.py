import json
import unittest
from chainpy.eth.ethtype.consts import ChainIndex, EnumInterface
from chainpy.eth.ethtype.hexbytes import EthHexBytes
from chainpy.eth.ethtype.utils import keccak_hash

BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS = 6
BOOTSTRAP_OFFSET_ROUNDS = 5


def sized_hex(a: int, a_size: int) -> str:
    limit = 2 ** (a_size << 3) - 1
    if a > limit:
        raise Exception("overflow")
    return "0x" + hex(a)[2:].zfill(a_size * 2)


def concat_2enum_as_int(a, b) -> int:
    a_hex, b_hex = sized_hex(a.value, a.size()), sized_hex(b.value, b.size())
    return int(a_hex + b_hex.replace("0x", ""), 16)


class SymbolIdx(EnumInterface):
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


class BridgeIndex(EnumInterface):
    NONE             = 0x00000000000000000000000000000000

    # tokens relate to the Bifrost coin
    BFC_BIFROST      = concat_2enum_as_int(SymbolIdx.BFC, ChainIndex.BIFROST)
    WBFC_BIFROST     = concat_2enum_as_int(SymbolIdx.WBFC, ChainIndex.BIFROST)

    # bitcoin
    BTC_BITCOIN      = concat_2enum_as_int(SymbolIdx.BTC, ChainIndex.BITCOIN)

    # tokens on the ethereum
    ETH_ETHEREUM     = concat_2enum_as_int(SymbolIdx.ETH, ChainIndex.ETHEREUM)
    DAI_ETHEREUM     = concat_2enum_as_int(SymbolIdx.DAI, ChainIndex.ETHEREUM)
    USDC_ETHEREUM    = concat_2enum_as_int(SymbolIdx.USDC, ChainIndex.ETHEREUM)
    USDT_ETHEREUM    = concat_2enum_as_int(SymbolIdx.USDT, ChainIndex.ETHEREUM)
    LINK_ETHEREUM    = concat_2enum_as_int(SymbolIdx.LINK, ChainIndex.ETHEREUM)
    BIFI_ETHEREUM = concat_2enum_as_int(SymbolIdx.BIFI, ChainIndex.ETHEREUM)

    BNB_BINANCE = concat_2enum_as_int(SymbolIdx.BNB, ChainIndex.BINANCE)
    BUSD_BINANCE = concat_2enum_as_int(SymbolIdx.BUSD, ChainIndex.BINANCE)
    USDC_BINANCE = concat_2enum_as_int(SymbolIdx.USDC, ChainIndex.BINANCE)

    MATIC_POLYGON = concat_2enum_as_int(SymbolIdx.MATIC, ChainIndex.POLYGON)

    # tokens on the klaytn
    KLAY_KLAYTN      = concat_2enum_as_int(SymbolIdx.KLAY, ChainIndex.KLAYTN)

    AVAX_AVALANCHE = concat_2enum_as_int(SymbolIdx.AVAX, ChainIndex.AVALANCHE)

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def size() -> int:
        return SymbolIdx.size() + ChainIndex.size()  # 16

    def home_chain_index(self) -> ChainIndex:
        value_bytes = EthHexBytes(self.value, self.size())
        return ChainIndex(value_bytes[SymbolIdx.size():])

    def token_name(self) -> str:
        return self.name.split("_")[0]

    def is_coin_on(self, chain_index: ChainIndex) -> bool:
        home_chain = self.home_chain_index()  # BIFROST
        if chain_index != home_chain:
            return False

        if home_chain == ChainIndex.BIFROST:
            return self == BridgeIndex.BFC_BIFROST
        if home_chain == ChainIndex.ETHEREUM:
            return self == BridgeIndex.ETH_ETHEREUM
        if home_chain == ChainIndex.BINANCE:
            return self == BridgeIndex.BNB_BINANCE
        if home_chain == ChainIndex.POLYGON:
            return self == BridgeIndex.MATIC_POLYGON
        if home_chain == ChainIndex.KLAYTN:
            return self == BridgeIndex.KLAY_KLAYTN
        if home_chain == ChainIndex.AVALANCHE:
            return self == BridgeIndex.AVAX_AVALANCHE
        raise Exception("Not supported chain: {}".format(home_chain))


class RBCMethodIndex(EnumInterface):
    NONE = 0x000000
    WARP = 0x010001
    WARP_UNIFY = 0x02000b
    DEPOSIT = 0x020002
    REPAY = 0x020003
    WARP_SWAP = 0x020004
    XOPEN = 0x020005
    CALL = 0x020006

    WITHDRAW = 0x030007
    BORROW = 0x030008
    SWAP_WARP = 0x030009
    XEND = 0x03000a

    WARP_SWAP_WARP = 0x03000c

    # CALL      = 0x03000b

    @staticmethod
    def size() -> int:
        return 8


class AggOracleId(EnumInterface):
    NONE = 0

    BFC_PRICE = SymbolIdx.BFC.value
    BTC_PRICE = SymbolIdx.BTC.value
    ETH_PRICE = SymbolIdx.ETH.value
    DAI_PRICE = SymbolIdx.DAI.value
    USDC_PRICE = SymbolIdx.USDC.value
    USDT_PRICE = SymbolIdx.USDT.value
    LINK_PRICE = SymbolIdx.LINK.value
    KLAY_PRICE = SymbolIdx.KLAY.value
    BNB_PRICE = SymbolIdx.BNB.value
    MATIC_PRICE = SymbolIdx.MATIC.value
    BIFI_PRICE = SymbolIdx.BIFI.value
    BUSD_PRICE = SymbolIdx.BUSD.value

    @staticmethod
    def size() -> int:
        return 32

    @classmethod
    def from_token_name(cls, token_name: str):
        return AggOracleId[token_name + "_PRICE"]


class ConsensusOracleId(EnumInterface):
    NONE = 0

    BTC_HASH = keccak_hash("bitcoinblockhash".encode()).int()

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
        enum_dict["TokenIndex"] = TestEnum.generate_dict_for_index(SymbolIdx)

        enum_dict["BridgeIndex"] = TestEnum.generate_dict_for_index(BridgeIndex)
        enum_dict["ChainEventStatus"] = TestEnum.generate_dict_for_index(ChainEventStatus)
        enum_dict["RBCMethodIndex"] = TestEnum.generate_dict_for_index(RBCMethodIndex)
        enum_dict["AggOracleId"] = TestEnum.generate_dict_for_index(AggOracleId)
        enum_dict["ConsensusOracleId"] = TestEnum.generate_dict_for_index(ConsensusOracleId)

        print(json.dumps(enum_dict, indent=4))
