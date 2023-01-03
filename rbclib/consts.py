import json
import unittest
from typing import Union, List, cast

from chainpy.eth.ethtype.consts import EnumInterface, Chain

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


class Symbol(EnumInterface):
    NONE = 0x00
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

    def is_coin_on(self, chain_index: Chain) -> bool:
        if self == Symbol.BFC and chain_index == Chain.BIFROST:
            return True
        if self == Symbol.BTC and chain_index == Chain.BITCOIN:
            return True
        if self == Symbol.ETH and chain_index == Chain.ETHEREUM:
            return True
        if self == Symbol.BNB and chain_index == Chain.ETHEREUM:
            return True
        if self == Symbol.MATIC and chain_index == Chain.POLYGON:
            return True
        if self == Symbol.KLAY and chain_index == Chain.KLAYTN:
            return True
        return False

    @property
    def decimal(self):
        return 6 if self == Symbol.USDC or self == Symbol.USDT else 18


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


# unified tokens on the bifrost network
UNIFIED_BTC_ON_BIFROST_ERC20_ADDRESS = "0x00000001"
UNIFIED_BFC_ON_ETHEREUM_ERC20_ADDRESS = "0x00000001"
UNIFIED_BIFI_ON_BIFROST_ERC20_ADDRESS = "0x00000001"
UNIFIED_ETH_ON_BIFROST_ERC20_ADDRESS = "0x00000001"
UNIFIED_BNB_ON_BIFROST_ERC20_ADDRESS = "0x00000001"
UNIFIED_AVAX_ON_BIFROST_ERC20_ADDRESS = "0x00000001"
UNIFIED_MATIC_ON_BIFROST_ERC20_ADDRESS = "0x00000001"
UNIFIED_USDC_ON_BIFROST_ERC20_ADDRESS = "0x00000001"
UNIFIED_BUSD_ON_BIFROST_ERC20_ADDRESS = "0x00000001"

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


class Asset(EnumInterface):
    NONE = 0
    BTC_ON_BITCOIN = concat_items_as_int(Symbol.BTC, Chain.BITCOIN, 0xffffffff)
    BTC_ON_BIFROST = concat_items_as_int(Symbol.BTC, Chain.BIFROST, BTC_ON_BIFROST_ERC20_ADDRESS)
    BTC_ON_ETHEREUM = concat_items_as_int(Symbol.BTC, Chain.ETHEREUM, BTC_ON_ETHEREUM_ERC20_ADDRESS)
    UNIFIED_BTC_ON_BIFROST = concat_items_as_int(Symbol.BTC, Chain.BIFROST, UNIFIED_BTC_ON_BIFROST_ERC20_ADDRESS)

    BFC_ON_BIFROST = concat_items_as_int(Symbol.BFC, Chain.BIFROST, 0xffffffff)
    BFC_ON_ETHEREUM = concat_items_as_int(Symbol.BFC, Chain.ETHEREUM, BFC_ON_ETHEREUM_ERC20_ADDRESS)
    UNIFIED_BFC_ON_BIFROST = concat_items_as_int(Symbol.BTC, Chain.BIFROST, UNIFIED_BFC_ON_ETHEREUM_ERC20_ADDRESS)

    BIFI_ON_BIFROST = concat_items_as_int(Symbol.BIFI, Chain.BIFROST, BIFI_ON_BIFROST_ERC20_ADDRESS)
    BIFI_ON_ETHEREUM = concat_items_as_int(Symbol.BIFI, Chain.ETHEREUM, BIFI_ON_ETHEREUM_ERC20_ADDRESS)
    UNIFIED_BIFI_ON_BIFROST = concat_items_as_int(Symbol.BIFI, Chain.BIFROST, UNIFIED_BIFI_ON_BIFROST_ERC20_ADDRESS)

    ETH_ON_BIFROST = concat_items_as_int(Symbol.ETH, Chain.BIFROST, ETH_ON_BIFROST_ERC20_ADDRESS)
    ETH_ON_ETHEREUM = concat_items_as_int(Symbol.ETH, Chain.ETHEREUM, 0xffffffff)
    UNIFIED_ETH_ON_BIFROST = concat_items_as_int(Symbol.ETH, Chain.BIFROST, UNIFIED_ETH_ON_BIFROST_ERC20_ADDRESS)

    BNB_ON_BIFROST = concat_items_as_int(Symbol.BNB, Chain.BIFROST, BNB_ON_BIFROST_ERC20_ADDRESS)
    BNB_ON_BINANCE = concat_items_as_int(Symbol.BNB, Chain.BINANCE, 0xffffffff)
    UNIFIED_BNB_ON_BIFROST = concat_items_as_int(Symbol.BNB, Chain.BIFROST, UNIFIED_BNB_ON_BIFROST_ERC20_ADDRESS)

    AVAX_ON_BIFROST = concat_items_as_int(Symbol.AVAX, Chain.BIFROST, AVAX_ON_BIFROST_ERC20_ADDRESS)
    AVAX_ON_AVALANCHE = concat_items_as_int(Symbol.AVAX, Chain.AVALANCHE, 0xffffffff)
    UNIFIED_AVAX_ON_BIFROST = concat_items_as_int(Symbol.AVAX, Chain.BIFROST, UNIFIED_AVAX_ON_BIFROST_ERC20_ADDRESS)

    MATIC_ON_BIFROST = concat_items_as_int(Symbol.MATIC, Chain.BIFROST, MATIC_ON_BIFROST_ERC20_ADDRESS)
    MATIC_ON_POLYGON = concat_items_as_int(Symbol.MATIC, Chain.BIFROST, 0xffffffff)
    UNIFIED_MATIC_ON_BIFROST = concat_items_as_int(Symbol.MATIC, Chain.BIFROST, UNIFIED_MATIC_ON_BIFROST_ERC20_ADDRESS)

    USDC_ON_BIFROST = concat_items_as_int(Symbol.USDC, Chain.BIFROST, USDC_ON_BIFROST_ERC20_ADDRESS)
    USDC_ON_ETHEREUM = concat_items_as_int(Symbol.USDC, Chain.ETHEREUM, USDC_ON_ETHEREUM_ERC20_ADDRESS)
    USDC_ON_BINANCE = concat_items_as_int(Symbol.USDC, Chain.BINANCE, USDC_ON_BINANCE_ERC20_ADDRESS)
    USDC_ON_AVALANCHE = concat_items_as_int(Symbol.USDC, Chain.AVALANCHE, USDC_ON_AVALANCHE_ERC20_ADDRESS)
    USDC_ON_POLYGON = concat_items_as_int(Symbol.USDC, Chain.POLYGON, USDC_ON_POLYGON_ERC20_ADDRESS)
    UNIFIED_USDC_ON_BIFROST = concat_items_as_int(Symbol.USDC, Chain.BIFROST, UNIFIED_USDC_ON_BIFROST_ERC20_ADDRESS)

    BUSD_ON_BIFROST = concat_items_as_int(Symbol.BUSD, Chain.BIFROST, BUSD_ON_BIFROST_ERC20_ADDRESS)
    BUSD_ON_BINANCE = concat_items_as_int(Symbol.BUSD, Chain.BINANCE, BUSD_ON_BINANCE_ERC20_ADDRESS)
    UNIFIED_BUSD_ON_BIFROST = concat_items_as_int(Symbol.BUSD, Chain.BIFROST, UNIFIED_BUSD_ON_BIFROST_ERC20_ADDRESS)

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [Symbol.str_with_size(), Chain.str_with_size(), "ADDRESS-4"]

    def analyze(self) -> (Symbol, Chain, str):
        """ symbol, related chain and erc20 address """
        return parser(self.formatted_hex(), [Symbol, Chain, ERC20_ADDRESS_BSIZE])

    @staticmethod
    def size():
        return Symbol.size() + Chain.size() + ERC20_ADDRESS_BSIZE

    def symbol(self) -> Symbol:
        return cast(Symbol, self.analyze()[0])

    def is_coin_on(self, chain_index: Chain) -> bool:
        return self.symbol().is_coin_on(chain_index)

    @property
    def decimal(self) -> int:
        return self.symbol().decimal


class Bridge(EnumInterface):
    NONE = 0x00

    BFC_BIFROST_ETHEREUM = concat_items_as_int(Asset.BFC_ON_BIFROST, Asset.BFC_ON_ETHEREUM, "0x01")
    BIFI_BIFROST_ETHEREUM = concat_items_as_int(Asset.BIFI_ON_BIFROST, Asset.BIFI_ON_ETHEREUM, "0x01")
    BTC_BITCOIN_BIFROST = concat_items_as_int(Asset.BTC_ON_BITCOIN, Asset.BTC_ON_BIFROST, "0x01")
    ETH_BIFROST_ETHEREUM = concat_items_as_int(Asset.ETH_ON_BIFROST, Asset.ETH_ON_BIFROST, "0x01")
    BNB_BIFROST_BINANCE = concat_items_as_int(Asset.BNB_ON_BIFROST, Asset.BNB_ON_BINANCE, "0x01")
    MATIC_BIFROST_POLYGON = concat_items_as_int(Asset.MATIC_ON_BIFROST, Asset.MATIC_ON_POLYGON, "0x01")
    AVAX_BIFROST_AVALANCHE = concat_items_as_int(Asset.AVAX_ON_BIFROST, Asset.AVAX_ON_AVALANCHE, "0x01")

    USDC_BIFROST_ETHEREUM = concat_items_as_int(Asset.USDC_ON_BIFROST, Asset.USDC_ON_ETHEREUM, "0x01")
    USDC_BIFROST_BINANCE = concat_items_as_int(Asset.USDC_ON_BIFROST, Asset.USDC_ON_BINANCE, "0x01")
    USDC_BIFROST_AVALANCHE = concat_items_as_int(Asset.USDC_ON_BIFROST, Asset.USDC_ON_AVALANCHE, "0x01")
    USDC_BIFROST_POLYGON = concat_items_as_int(Asset.USDC_ON_BIFROST, Asset.USDC_ON_POLYGON, "0x01")

    BUSD_BIFROST_ETHEREUM = concat_items_as_int(Asset.BUSD_ON_BIFROST, Asset.BUSD_ON_BINANCE, "0x01")

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [Asset.str_with_size(), Asset.str_with_size(), "DISTINGUISH_BYTE-1"]

    @staticmethod
    def size() -> int:
        return Asset.size() * 2 + DISTINGUISH_NUM_BSIZE

    def analyze(self) -> (Asset, Asset, int):
        """ parse 2 indices and duplicate-prevention number"""
        return parser(self.formatted_hex(), [Asset, Asset, DISTINGUISH_NUM_BSIZE])

    def symbol(self) -> Symbol:
        return cast(Asset, self.analyze()[0]).symbol()

    def is_coin_on(self, chain_index: Chain) -> bool:
        return self.symbol().is_coin_on(chain_index)

    @property
    def decimal(self) -> int:
        return self.symbol().decimal


class OPCode(EnumInterface):
    NONE = 0x00
    WARP = 0x01
    UNIFY = 0x02
    SPLIT = 0x03
    UNIFY_SPLIT = 0x04
    DEPOSIT = 0x05
    WITHDRAW = 0x06
    BORROW = 0x07
    REPAY = 0x08
    X_OPEN = 0x09
    X_END = 0x0a
    SWAP = 0x0b
    CALL = 0x0c

    @staticmethod
    def size():
        return 1

    @staticmethod
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []


class RBCMethodDirection(EnumInterface):
    NONE = 0x00
    INBOUND = 0x01
    OUTBOUND = 0x02
    IN_AND_OUTBOUND = 0x03

    @staticmethod
    def is_composed() -> bool:
        return False

    @staticmethod
    def components() -> List[str]:
        return []

    @staticmethod
    def size() -> int:
        return 1


class RBCMethodV1(EnumInterface):
    NONE = 0x0000000000000000
    WARP_IN = concat_items_as_int(2, RBCMethodDirection.INBOUND, OPCode.WARP)
    WARP_UNIFY = concat_items_as_int(3, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY)
    WARP_UNIFY_DEPOSIT = concat_items_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.DEPOSIT)
    WARP_UNIFY_REPAY = concat_items_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.REPAY)
    WARP_UNIFY_SWAP = concat_items_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.SWAP)
    WARP_XOPEN = concat_items_as_int(4, RBCMethodDirection.INBOUND, OPCode.WARP, OPCode.UNIFY, OPCode.X_OPEN)
    WARP_CALL = concat_items_as_int(3, RBCMethodDirection.INBOUND, OPCode.CALL, OPCode.WARP)

    WARP_OUT = concat_items_as_int(2, RBCMethodDirection.OUTBOUND, OPCode.WARP)
    SPLIT_WARP = concat_items_as_int(3, RBCMethodDirection.OUTBOUND, OPCode.SPLIT, OPCode.WARP)
    BORROW_SPLIT_WARP = concat_items_as_int(4, RBCMethodDirection.OUTBOUND, OPCode.BORROW, OPCode.SPLIT, OPCode.WARP)
    WITHDRAW_SPLIT_WARP = concat_items_as_int(4, RBCMethodDirection.OUTBOUND, OPCode.WITHDRAW, OPCode.SPLIT, OPCode.WARP)
    SWAP_SPLIT_WARP = concat_items_as_int(4, RBCMethodDirection.OUTBOUND, OPCode.SWAP, OPCode.SPLIT, OPCode.WARP)
    XEND_SPLIT_WARP = concat_items_as_int(4, RBCMethodDirection.OUTBOUND, OPCode.X_END, OPCode.SPLIT, OPCode.WARP)
    CALL_WARP = concat_items_as_int(3, RBCMethodDirection.OUTBOUND, OPCode.CALL, OPCode.WARP)

    WARP_SWAP_WARP = concat_items_as_int(4, RBCMethodDirection.IN_AND_OUTBOUND, OPCode.WARP, OPCode.SWAP, OPCode.WARP)
    WARP_UNIFY_SPLIT_WARP = concat_items_as_int(4, RBCMethodDirection.IN_AND_OUTBOUND, OPCode.WARP, OPCode.UNIFY_SPLIT, OPCode.WARP)
    WARP_UNIFY_SWAP_SPLIT_WARP = concat_items_as_int(
        6, RBCMethodDirection.IN_AND_OUTBOUND, OPCode.WARP, OPCode.SPLIT, OPCode.SWAP, OPCode.UNIFY, OPCode.WARP
    )

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [
            "LENGTH-1",
            RBCMethodDirection.str_with_size(),
            "DYNAMIC_SIZE_ARRAY[{}]".format(OPCode.str_with_size())]

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
        return 16


class OracleType(EnumInterface):
    NONE = 0x00
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
    NONE = 0x00
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


class Oracle(EnumInterface):
    NONE = 0
    BFC_BIFROST_ETHEREUM_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.BFC_BIFROST_ETHEREUM)
    BIFI_BIFROST_ETHEREUM_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.BIFI_BIFROST_ETHEREUM)
    BTC_BITCOIN_BIFROST_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.BTC_BITCOIN_BIFROST)
    ETH_BIFROST_ETHEREUM_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.ETH_BIFROST_ETHEREUM)
    BNB_BIFROST_BINANCE_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.BNB_BIFROST_BINANCE)
    MATIC_BIFROST_POLYGON_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.MATIC_BIFROST_POLYGON)
    AVAX_BIFROST_AVALANCHE_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.AVAX_BIFROST_AVALANCHE)

    USDC_BIFROST_ETHEREUM_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.USDC_BIFROST_ETHEREUM)
    BUSD_BIFROST_ETHEREUM_PRICE = concat_items_as_int(OracleType.AGGREGATED, OracleSourceType.ASSET_PRICE, Bridge.BUSD_BIFROST_ETHEREUM)

    BITCOIN_BLOCK_HASH = concat_items_as_int(OracleType.CONSENSUS, OracleSourceType.BLOCK_HASH, Bridge.BTC_BITCOIN_BIFROST)

    @staticmethod
    def is_composed() -> bool:
        return True

    @staticmethod
    def components() -> List[str]:
        return [OracleType.str_with_size(), OracleSourceType.str_with_size(), Bridge.str_with_size()]

    def analyze(self):
        return parser(self.formatted_hex(), [OracleType, OracleSourceType, Bridge])

    @staticmethod
    def size() -> int:
        return OracleType.size() + OracleSourceType.size() + Bridge.size()

    def formatted_hex(self) -> str:
        if self == self.__class__.NONE:
            return "0x" + "00" * self.size()
        zero_pad = "00" * (self.size() - OracleType.size() - OracleSourceType.size() - Bridge.size())
        return to_even_hex(self.value) + zero_pad

    def formatted_bytes(self) -> bytes:
        return bytes.fromhex(self.formatted_hex().replace("0x", ""))

    @classmethod
    def from_bridge(cls, bridge: Bridge):
        return Oracle[bridge.name + "_PRICE"]


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
        enum_dict["Chain"] = TestEnum.generate_dict_for_index(Chain)
        enum_dict["Symbol"] = TestEnum.generate_dict_for_index(Symbol)
        enum_dict["Asset"] = TestEnum.generate_dict_for_index(Asset)
        enum_dict["Bridge"] = TestEnum.generate_dict_for_index(Bridge)

        enum_dict["OPCode"] = TestEnum.generate_dict_for_index(OPCode)
        enum_dict["RBCMethodDirection"] = TestEnum.generate_dict_for_index(RBCMethodDirection)
        enum_dict["RBCMethodV1"] = TestEnum.generate_dict_for_index(RBCMethodV1)

        enum_dict["OracleType"] = TestEnum.generate_dict_for_index(OracleType)
        enum_dict["OracleSourceType"] = TestEnum.generate_dict_for_index(OracleSourceType)
        enum_dict["Oracle"] = TestEnum.generate_dict_for_index(Oracle)
        enum_dict["ChainEventStatus"] = TestEnum.generate_dict_for_index(ChainEventStatus)

        print(json.dumps(enum_dict, indent=4))

        # print(BridgeIndex.BFC_BIFROST_ETHEREUM.analyze())
