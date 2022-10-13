import json
import os
import time
from typing import List, Tuple, Dict, Optional

from ..eth.managers.configs import EntityRootConfig
from ..eth.managers.eventhandler import DetectedEvent
from ..eth.ethtype.chaindata import EthLog
from ..eth.ethtype.consts import ChainIndex
from ..utils import ensure_path_endswith_slash_char


def timestamp_msec() -> int:
    return int(time.time() * 1000)


def safe_create_directory(path_: str):
    if not os.path.exists(path_):
        os.makedirs(path_)


EventDict = Optional[Dict[str, List[DetectedEvent]]]
RangesDict = Optional[Dict[ChainIndex, Tuple[int, int]]]


def load_events_from_file(entity_cache_dir_path: str) -> (EventDict, RangesDict):
    # formatting cache file path and create target directory if not exists
    entity_cache_dir_path = ensure_path_endswith_slash_char(entity_cache_dir_path)
    safe_create_directory(entity_cache_dir_path)

    detected_events_dict = dict()
    ranges = dict()
    try:
        with open(entity_cache_dir_path + "ranges.json", "r") as json_data:
            ranges_json = json.load(json_data)
            for chain_name, _range in ranges_json.items():
                chain_index = eval("ChainIndex." + chain_name)
                ranges[chain_index] = _range
    except FileNotFoundError:
        return None, None

    # get name of the latest cache file
    file_names = os.listdir(entity_cache_dir_path)
    file_names.remove("ranges.json")

    for file_name in file_names:
        with open(entity_cache_dir_path + file_name, "r") as json_data:
            file_db = json.load(json_data)
            loaded_events = eval(file_db["event"])

            detected_events = list()
            for event in loaded_events:
                event_obj = DetectedEvent(
                    eval("ChainIndex." + event["chain_name"].upper()),
                    event["contract_name"],
                    event["event_name"],
                    EthLog.from_dict(event["log"])
                )
                detected_events.append(event_obj)

            event_name = file_name.split(".")[0]
            detected_events_dict[event_name] = detected_events

    return detected_events_dict, ranges


def write_events_to_file(
        cache_dir_path: str,
        ranges: Dict[ChainIndex, Tuple[int, int]],
        events_dict: Dict[str, List[DetectedEvent]]):

    if cache_dir_path is None:
        return

    cache_dir_path = ensure_path_endswith_slash_char(cache_dir_path)
    safe_create_directory(cache_dir_path)

    with open(cache_dir_path + "ranges.json", "w") as f:
        serialized_ranges = dict()
        for key, value in ranges.items():
            serialized_ranges[key.name] = value
        json.dump(serialized_ranges, f)

    for event_name, events in events_dict.items():
        ref_event = events[0]
        file_name = "{}.json".format(event_name)

        events_to_write = list()
        for event in events:
            if event.event_name != ref_event.event_name:
                raise Exception("Not matched event name of the event")
            events_to_write.append(event.to_dict())

        # export new file
        with open(cache_dir_path + file_name, "w") as f:
            json.dump({"event": str(events_to_write)}, f)


def transaction_commit_time_sec(chain_index: ChainIndex, root_config: EntityRootConfig) -> int:
    chain_config = root_config.get_chain_config(chain_index)
    block_aging_time_sec = chain_config.block_aging_period * chain_config.block_period_sec
    return block_aging_time_sec * chain_config.transaction_commit_multiplier
