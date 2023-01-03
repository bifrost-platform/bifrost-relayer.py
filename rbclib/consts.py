import json
import unittest
from typing import Union, List, cast

from chainpy.eth.ethtype.consts import EnumInterface, ChainIdx

BIFROST_VALIDATOR_HISTORY_LIMIT_BLOCKS = 6
BOOTSTRAP_OFFSET_ROUNDS = 5


def to_even_hex(a: Union[str, int]) -> str:
    if isinstance(a, str):
        hex_value = "0x" + a if not a.startswith("0x") else a
    elif isinstance(a, int):
        hex_value = hex(a)
    else:
        raise Exception("Input with unexpected typed: {}".format(type(a)))

    return "0x0" + hex_value.replace("0x", "") if len(hex_value) % 2 == 1 else hex_value


def zero_filled_hex(a: int, a_size: int) -> str:
    limit = 2 ** (a_size << 3) - 1
    if a > limit:
        raise Exception("overflow")
    return "0x" + hex(a).replace("0x", "").zfill(a_size * 2)


def concat_hexes(*args) -> str:
    ret_hex = ""
    for arg in args:
        if ret_hex == "":
            ret_hex = to_even_hex(arg)
        else:
            ret_hex += arg.replace("0x", "")
    return ret_hex


def concat_items_as_hex(*args) -> str:
    hexes = list()
    for arg in args:
        if issubclass(type(arg), EnumInterface):
            arg_hex = zero_filled_hex(arg.value, arg.size())
            hexes.append(arg_hex)
        elif isinstance(arg, int) or isinstance(arg, str):
            arg_hex = to_even_hex(arg)
            hexes.append(arg_hex)
        else:
            raise Exception("Input with unexpected typed: {}".format(type(arg)))
    return concat_hexes(*hexes)


def concat_items_as_int(*args) -> int:
    return int(concat_items_as_hex(*args), 16)


def parser(hex_str: str, element_types: List[Union[int, type]]) -> List[Union[int, type]]:
    hex_without_0x = hex_str.replace("0x", "")

    start, end = 0, 0
    elements = list()

    for _type in element_types:
        if isinstance(_type, int):
            start, end = end, end + _type * 2
            enc = lambda x: hex(x)
        elif issubclass(_type, EnumInterface):
            start, end = end, end + _type.size() * 2
            enc = lambda x: _type(x)
        else:
            raise Exception()
        elements.append(enc(int(hex_without_0x[start:end], 16)))

    return elements


class SymbolIdx(EnumInterface):
    BFC  = 0x01
    BIFI = 0x2
    BTC  = 0x3
    ETH  = 0x4
    BNB = 0x5
    MATIC = 0x6
    AVAX = 0x7
    USDC = 0x8
    BUSD = 0x9
    USDT = 0xa
    DAI  = 0xb
    LINK = 0xc
    KLAY = 0xd

    @staticmethod
    def size():
        return 4

    @staticmethod
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []

    def is_coin_on(self, chain_index: ChainIdx) -> bool:
        if self == SymbolIdx.BFC and chain_index == ChainIdx.BIFROST:
            return True
        if self == SymbolIdx.BTC and chain_index == ChainIdx.BITCOIN:
            return True
        if self == SymbolIdx.ETH and chain_index == ChainIdx.ETHEREUM:
            return True
        if self == SymbolIdx.BNB and chain_index == ChainIdx.ETHEREUM:
            return True
        if self == SymbolIdx.MATIC and chain_index == ChainIdx.POLYGON:
            return True
        if self == SymbolIdx.KLAY and chain_index == ChainIdx.KLAYTN:
            return True
        return False


ERC20_ADDRESS_BSIZE = 4
DISTINGUISH_NUM_BSIZE = 1

# tokens on the bifrost network
BTC_ON_BIFROST_ERC20_ADDRESS = "0x00000000"
BIFI_ON_BIFROST_ERC20_ADDRESS = "0x00000000"
ETH_ON_BIFROST_ERC20_ADDRESS = "0x00000000"
BNB_ON_BIFROST_ERC20_ADDRESS = "0x00000000"
AVAX_ON_BIFROST_ERC20_ADDRESS = "0x00000000"
MATIC_ON_BIFROST_ERC20_ADDRESS = "0x00000000"
USDC_ON_BIFROST_ERC20_ADDRESS = "0x00000000"
BUSD_ON_BIFROST_ERC20_ADDRESS = "0x00000000"

# tokens on the ethereum
BTC_ON_ETHEREUM_ERC20_ADDRESS = "0x00000000"
BFC_ON_ETHEREUM_ERC20_ADDRESS = "0x00000000"
BIFI_ON_ETHEREUM_ERC20_ADDRESS = "0x00000000"
USDC_ON_ETHEREUM_ERC20_ADDRESS = "0x00000000"


# tokens on the binance chain
USDC_ON_BINANCE_ERC20_ADDRESS = "0x00000000"
BUSD_ON_BINANCE_ERC20_ADDRESS = "0x00000000"

# tokens on the polygon
USDC_ON_POLYGON_ERC20_ADDRESS = "0x00000000"


# tokens on the avalanche
USDC_ON_AVALANCHE_ERC20_ADDRESS = "0x00000000"


class AssetIdx(EnumInterface):
    BTC_ON_BITCOIN = concat_items_as_int(SymbolIdx.BTC, ChainIdx.BITCOIN, 0xffffffff)
    BTC_ON_BIFROST = concat_items_as_int(SymbolIdx.BTC, ChainIdx.BIFROST, BTC_ON_BIFROST_ERC20_ADDRESS)
    BTC_ON_ETHEREUM = concat_items_as_int(SymbolIdx.BTC, ChainIdx.ETHEREUM, BTC_ON_ETHEREUM_ERC20_ADDRESS)

    BFC_ON_BIFROST = concat_items_as_int(SymbolIdx.BFC, ChainIdx.BIFROST, 0xffffffff)
    BFC_ON_ETHEREUM = concat_items_as_int(SymbolIdx.BFC, ChainIdx.ETHEREUM, BFC_ON_ETHEREUM_ERC20_ADDRESS)

    BIFI_ON_BIFROST = concat_items_as_int(SymbolIdx.BIFI, ChainIdx.BIFROST, BIFI_ON_BIFROST_ERC20_ADDRESS)
    BIFI_ON_ETHEREUM = concat_items_as_int(SymbolIdx.BIFI, ChainIdx.ETHEREUM, BIFI_ON_ETHEREUM_ERC20_ADDRESS)

    ETH_ON_BIFROST = concat_items_as_int(SymbolIdx.ETH, ChainIdx.BIFROST, ETH_ON_BIFROST_ERC20_ADDRESS)
    ETH_ON_ETHEREUM = concat_items_as_int(SymbolIdx.ETH, ChainIdx.ETHEREUM, 0xffffffff)

    BNB_ON_BIFROST = concat_items_as_int(SymbolIdx.BNB, ChainIdx.BIFROST, BNB_ON_BIFROST_ERC20_ADDRESS)
    BNB_ON_BINANCE = concat_items_as_int(SymbolIdx.BNB, ChainIdx.BINANCE, 0xffffffff)

    AVAX_ON_BIFROST = concat_items_as_int(SymbolIdx.AVAX, ChainIdx.BIFROST, AVAX_ON_BIFROST_ERC20_ADDRESS)
    AVAX_ON_AVALANCHE = concat_items_as_int(SymbolIdx.AVAX, ChainIdx.AVALANCHE, 0xffffffff)

    MATIC_ON_BIFROST = concat_items_as_int(SymbolIdx.MATIC, ChainIdx.BIFROST, MATIC_ON_BIFROST_ERC20_ADDRESS)
    MATIC_ON_POLYGON = concat_items_as_int(SymbolIdx.MATIC, ChainIdx.BIFROST, 0xffffffff)

    USDC_ON_BIFROST = concat_items_as_int(SymbolIdx.USDC, ChainIdx.BIFROST, USDC_ON_BIFROST_ERC20_ADDRESS)
    USDC_ON_ETHEREUM = concat_items_as_int(SymbolIdx.USDC, ChainIdx.ETHEREUM, USDC_ON_ETHEREUM_ERC20_ADDRESS)
    USDC_ON_BINANCE = concat_items_as_int(SymbolIdx.USDC, ChainIdx.BINANCE, USDC_ON_BINANCE_ERC20_ADDRESS)
    USDC_ON_AVALANCHE = concat_items_as_int(SymbolIdx.USDC, ChainIdx.AVALANCHE, USDC_ON_AVALANCHE_ERC20_ADDRESS)
    USDC_ON_POLYGON = concat_items_as_int(SymbolIdx.USDC, ChainIdx.POLYGON, USDC_ON_POLYGON_ERC20_ADDRESS)

    BUSD_ON_BIFROST = concat_items_as_int(SymbolIdx.BUSD, ChainIdx.BIFROST, BUSD_ON_BIFROST_ERC20_ADDRESS)
    BUSD_ON_BINANCE = concat_items_as_int(SymbolIdx.BUSD, ChainIdx.BINANCE, BUSD_ON_BINANCE_ERC20_ADDRESS)

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [SymbolIdx.__name__, ChainIdx.__name__, "ADDRESS-4"]

    def analyze(self) -> (SymbolIdx, ChainIdx, str):
        """ symbol, related chain and erc20 address """
        return parser(self.formatted_hex(), [SymbolIdx, ChainIdx, ERC20_ADDRESS_BSIZE])

    @staticmethod
    def size():
        return SymbolIdx.size() + ChainIdx.size() + ERC20_ADDRESS_BSIZE

    def symbol(self) -> SymbolIdx:
        return cast(SymbolIdx, self.analyze()[0])

    def is_coin_on(self, chain_index: ChainIdx) -> bool:
        return self.symbol().is_coin_on(chain_index)


class BridgeIndex(EnumInterface):
    NONE = 0x00

    BFC_BIFROST_ETHEREUM = concat_items_as_int(AssetIdx.BFC_ON_BIFROST, AssetIdx.BFC_ON_ETHEREUM, "0x00")
    BIFI_BIFROST_ETHEREUM = concat_items_as_int(AssetIdx.BIFI_ON_BIFROST, AssetIdx.BIFI_ON_ETHEREUM, "0x00")
    BTC_BITCOIN_BIFROST = concat_items_as_int(AssetIdx.BTC_ON_BITCOIN, AssetIdx.BTC_ON_BIFROST, "0x00")
    ETH_BIFROST_ETHEREUM = concat_items_as_int(AssetIdx.ETH_ON_BIFROST, AssetIdx.ETH_ON_BIFROST, "0x00")
    BNB_BIFROST_BINANCE = concat_items_as_int(AssetIdx.BNB_ON_BIFROST, AssetIdx.BNB_ON_BINANCE, "0x00")
    MATIC_BIFROST_POLYGON = concat_items_as_int(AssetIdx.MATIC_ON_BIFROST, AssetIdx.MATIC_ON_POLYGON, "0x00")
    AVAX_BIFROST_AVALANCHE = concat_items_as_int(AssetIdx.AVAX_ON_BIFROST, AssetIdx.AVAX_ON_AVALANCHE, "0x00")

    USDC_BIFROST_ETHEREUM = concat_items_as_int(AssetIdx.USDC_ON_BIFROST, AssetIdx.USDC_ON_ETHEREUM, "0x00")
    USDC_BIFROST_BINANCE = concat_items_as_int(AssetIdx.USDC_ON_BIFROST, AssetIdx.USDC_ON_BINANCE, "0x00")
    USDC_BIFROST_AVALANCHE = concat_items_as_int(AssetIdx.USDC_ON_BIFROST, AssetIdx.USDC_ON_AVALANCHE, "0x00")
    USDC_BIFROST_POLYGON = concat_items_as_int(AssetIdx.USDC_ON_BIFROST, AssetIdx.USDC_ON_POLYGON, "0x00")

    BUSD_BIFROST_ETHEREUM = concat_items_as_int(AssetIdx.BUSD_ON_BIFROST, AssetIdx.BUSD_ON_BINANCE, "0x00")

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [AssetIdx.__name__, AssetIdx.__name__, "DISTINGUISH_BYTE-1"]

    @staticmethod
    def size() -> int:
        return AssetIdx.size() * 2 + DISTINGUISH_NUM_BSIZE

    def analyze(self) -> (AssetIdx, AssetIdx, int):
        """ parse 2 indices and duplicate-prevention number"""
        return parser(self.formatted_hex(), [AssetIdx, AssetIdx, DISTINGUISH_NUM_BSIZE])

    def symbol(self) -> SymbolIdx:
        return cast(self.analyze()[0], SymbolIdx).symbol()

    def is_coin_on(self, chain_index: ChainIdx) -> bool:
        return self.symbol().is_coin_on(chain_index)


class OPCode(EnumInterface):
    NONE = 0x00
    INBOUND = 0x01
    OUTBOUND = 0x02
    IN_AND_OUTBOUND = 0x03
    WARP = 0x04
    UNIFY = 0x05
    SPLIT = 0x06
    UNIFY_SPLIT = 0x07
    DEPOSIT = 0x08
    WITHDRAW = 0x09
    BORROW = 0xa
    REPAY = 0xb
    X_OPEN = 0xc
    X_END = 0xd
    SWAP = 0xe
    CALL = 0xf

    @staticmethod
    def size():
        return 1

    @staticmethod
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []


class RBCMethodIdxV1(EnumInterface):
    NONE = 0x0000000000000000
    WARP_IN = concat_items_as_int(2, OPCode.INBOUND, OPCode.WARP)
    WARP_UNIFY = concat_items_as_int(3, OPCode.INBOUND, OPCode.WARP, OPCode.UNIFY)
    WARP_UNIFY_DEPOSIT = concat_items_as_int(4, OPCode.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.DEPOSIT)
    WARP_UNIFY_REPAY = concat_items_as_int(4, OPCode.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.REPAY)
    WARP_UNIFY_SWAP = concat_items_as_int(4, OPCode.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.SWAP)
    WARP_XOPEN = concat_items_as_int(4, OPCode.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.X_OPEN)
    WARP_CALL = concat_items_as_int(3, OPCode.INBOUND, OPCode.CALL, OPCode.WARP)

    WARP_OUT = concat_items_as_int(2, OPCode.OUTBOUND, OPCode.WARP)
    SPLIT_WARP = concat_items_as_int(3, OPCode.OUTBOUND, OPCode.SPLIT, OPCode.WARP)
    BORROW_SPLIT_WARP = concat_items_as_int(4, OPCode.OUTBOUND, OPCode.BORROW, OPCode.SPLIT, OPCode.WARP)
    WITHDRAW_SPLIT_WARP = concat_items_as_int(4, OPCode.OUTBOUND, OPCode.WITHDRAW, OPCode.SPLIT, OPCode.WARP)
    SWAP_SPLIT_WARP = concat_items_as_int(4, OPCode.OUTBOUND, OPCode.SWAP, OPCode.SPLIT, OPCode.WARP)
    XEND_SPLIT_WARP = concat_items_as_int(4, OPCode.OUTBOUND, OPCode.X_END, OPCode.SPLIT, OPCode.WARP)
    CALL_WARP = concat_items_as_int(3, OPCode.OUTBOUND, OPCode.CALL, OPCode.WARP)

    WARP_SWAP_WARP = concat_items_as_int(4, OPCode.IN_AND_OUTBOUND, OPCode.WARP, OPCode.SWAP, OPCode.WARP)
    WARP_UNIFY_SPLIT_WARP = concat_items_as_int(4, OPCode.IN_AND_OUTBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT, OPCode.WARP)
    WARP_UNIFY_SWAP_SPLIT_WARP = concat_items_as_int(
        6, OPCode.IN_AND_OUTBOUND, OPCode.WARP, OPCode.SPLIT, OPCode.SWAP, OPCode.UNIFY, OPCode.WARP
    )

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return ["NUM_OF_OPCODE(1B)", "DYNAMIC_SIZE_ARRAY[{}]".format(OPCode.__name__)]

    def analyze(self) -> (int, List[OPCode]):
        self_hex = self.formatted_hex().replace("0x", "")
        len_op, self_hex = int(self_hex[:2], 16), self_hex[2:]

        start, end = 0, 0
        op_code_list = list()
        for i in range(len_op):
            op_code_list.append(OPCode(int(self_hex[i * OPCode.size() * 2:(i + 1) * OPCode.size() * 2], 16)))
            self_hex = self_hex[end:]
        return len_op, op_code_list

    def formatted_hex(self) -> str:
        if self == self.__class__.NONE:
            return "0x" + "00" * self.size()

        hex_without_0x = to_even_hex(self.value).replace("0x", "")
        op_num = int(hex_without_0x[:2], 16)
        zero_pad = "00" * (self.size() - op_num * OPCode.size() + 2)
        return "0x" + hex_without_0x + zero_pad

    def formatted_bytes(self) -> bytes:
        return bytes.fromhex(self.formatted_hex().replace("0x", ""))

    @staticmethod
    def size():
        return 32


class OracleType(EnumInterface):
    AGGREGATED = 0x01
    CONSENSUS = 0x02

    @staticmethod
    def size():
        """ bytes size """
        return 1

    @staticmethod
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []


class OracleSourceType(EnumInterface):
    ASSET_PRICE = 0x01
    BLOCK_HASH = 0x02

    @staticmethod
    def size():
        """ bytes size """
        return 2

    @staticmethod
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []


class OracleIdx(EnumInterface):
    NONE = 0
    BFC_PRICE_ON_ETHEREUM = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.BFC_ON_ETHEREUM)
    BIFI_PRICE_ON_ETHEREUM = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.BIFI_ON_ETHEREUM)
    BTC_PRICE_ON_BITCOIN = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.BTC_ON_BITCOIN)
    ETH_PRICE_ON_ETHEREUM = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.ETH_ON_ETHEREUM)
    BNB_PRICE_ON_BINANCE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.BNB_ON_BINANCE)
    MATIC_PRICE_ON_POLYGON = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.MATIC_ON_POLYGON)
    AVAX_PRICE_ON_AVALANCHE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.AVAX_ON_AVALANCHE)

    USDC_PRICE_ON_ETHEREUM = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.USDC_ON_ETHEREUM)
    BUSD_PRICE_ON_BINANCE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, AssetIdx.BUSD_ON_BINANCE)

    BITCOIN_BLOCK_HASH = concat_items_as_int(OracleType.CONSENSUS, OracleSourceType.BLOCK_HASH, AssetIdx.BTC_ON_BITCOIN)

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [OracleType.__name__, OracleType.__name__, AssetIdx.__name__]

    def analyze(self):
        return parser(self.formatted_hex(), [OracleType, OracleSourceType, AssetIdx])

    @staticmethod
    def size() -> int:
        return 32

    def formatted_hex(self) -> str:
        if self == self.__class__.NONE:
            return "0x" + "00" * self.size()
        zero_pad = "00" * (self.size() - OracleType.size() - OracleSourceType.size() - AssetIdx.size())
        return to_even_hex(self.value) + zero_pad

    def formatted_bytes(self) -> bytes:
        return bytes.fromhex(self.formatted_hex().replace("0x", ""))


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
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []

    @staticmethod
    def size():
        return 1


class TestEnum(unittest.TestCase):

    @staticmethod
    def generate_dict_for_index(index_type):
        index_dict = {
            "bsize": index_type.size(),
            "composed": index_type.is_composed(),
            "components": index_type.components()
        }

        for idx in index_type:
            index_dict[idx.name] = idx.formatted_hex()
        return index_dict

    def test_print_enum(self):
        enum_dict = {}
        enum_dict["ChainIndex"] = TestEnum.generate_dict_for_index(ChainIdx)
        enum_dict["SymbolIdx"] = TestEnum.generate_dict_for_index(SymbolIdx)
        enum_dict["AssetIdx"] = TestEnum.generate_dict_for_index(AssetIdx)
        enum_dict["BridgeIndex"] = TestEnum.generate_dict_for_index(BridgeIndex)

        enum_dict["OPCode"] = TestEnum.generate_dict_for_index(OPCode)
        enum_dict["RBCMethodIndex"] = TestEnum.generate_dict_for_index(RBCMethodIdxV1)

        enum_dict["OracleType"] = TestEnum.generate_dict_for_index(OracleType)
        enum_dict["OracleSourceType"] = TestEnum.generate_dict_for_index(OracleSourceType)
        enum_dict["OracleIdx"] = TestEnum.generate_dict_for_index(OracleIdx)
        enum_dict["ChainEventStatus"] = TestEnum.generate_dict_for_index(ChainEventStatus)

        print(json.dumps(enum_dict, indent=4))

        # print(BridgeIndex.BFC_BIFROST_ETHEREUM.analyze())
