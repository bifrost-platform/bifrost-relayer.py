from bridgeconst.consts import Chain, Symbol, Asset

from rbclib.switchable_enum import SwitchableChain


def symbol_to_asset(chain: Chain, symbol: Symbol) -> Asset:
    if chain == SwitchableChain.BIFROST and symbol == Symbol.BFC:
        asset_name = "_".join([symbol.name, "ON", chain.name])
    elif chain == SwitchableChain.BIFROST:
        asset_name = "_".join(["UNIFIED", symbol.name, "ON", SwitchableChain.BIFROST.name])
    else:
        asset_name = "_".join([symbol.name, "ON", chain.name])
    return Asset.from_name(asset_name)
