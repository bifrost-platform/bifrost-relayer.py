import json
from typing import Union, List, Dict


def to_list(targets: Union[str, list]) -> list:
    return targets.split(",") if isinstance(targets, str) else targets


def get_url_from_private_config(price_src_id: str, config_path: str = "../configs/entity.relayer.private.json") -> str:
    price_src_id_preset = ["Coingecko", "Upbit", "Chainlink"]

    if price_src_id not in price_src_id_preset:
        raise Exception("Not supported price source: {}".format(price_src_id))

    with open(config_path, "r") as f:
        config = json.load(f)

    return config["oracle_config"]["asset_prices"]["urls"][price_src_id]


def get_urls_from_private_config(config_path: str = "../configs/entity.relayer.private.json") -> Dict[str, str]:
    with open(config_path, "r") as f:
        config = json.load(f)

    return config["oracle_config"]["asset_prices"]["urls"]
