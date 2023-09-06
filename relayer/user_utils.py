from bridgeconst.consts import Chain, Symbol, Asset

from rbclib.primitives.relay_chain import chain_enum


def symbol_to_asset(chain: Chain, symbol: Symbol) -> Asset:
    if chain == chain_enum.BIFROST and symbol == Symbol.BFC:
        asset_name = "_".join([symbol.name, "ON", chain.name])
    elif chain == chain_enum.BIFROST:
        asset_name = "_".join(["UNIFIED", symbol.name, "ON", chain_enum.BIFROST.name])
    else:
        asset_name = "_".join([symbol.name, "ON", chain.name])
    return Asset.from_name(asset_name)
