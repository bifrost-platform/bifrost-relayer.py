from bridgeconst.consts import Chain, Symbol, Asset

from rbclib.primitives.relay_chain import chain_primitives


def symbol_to_asset(chain: Chain, symbol: Symbol) -> Asset:
    if chain == chain_primitives.BIFROST and symbol == Symbol.BFC:
        asset_name = "_".join([symbol.name, "ON", chain.name])
    elif chain == chain_primitives.BIFROST:
        asset_name = "_".join(["UNIFIED", symbol.name, "ON", chain_primitives.BIFROST.name])
    else:
        asset_name = "_".join([symbol.name, "ON", chain.name])
    return Asset.from_name(asset_name)
