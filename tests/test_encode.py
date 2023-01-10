import json

from chainpy.eth.managers.eventobj import DetectedEvent
from chainpy.eventbridge.eventbridge import EventBridge

from rbclib.chainevents import RbcEvent


REQUESTED1_DETECTED_EVENT_JSON = "./events_json/detected_requested1.json"
EXECUTED_DETECTED_EVENT_JSON = "./events_json/detected_executed.json"
ACCEPTED_DETECTED_EVENT_JSON = "./events_json/detected_accepted.json"
COMMITTED_DETECTED_EVENT_JSON = "./events_json/detected_committed.json"

REQUESTED2_DETECTED_EVENT_JSON = "./events_json/detected_requested2.json"
REJECTED_DETECTED_EVENT_JSON = "./events_json/detected_rejected.json"
REVERTED_DETECTED_EVENT_JSON = "./events_json/detected_reverted.json"
ROLLBACKED_DETECTED_EVENT_JSON = "./events_json/detected_event6.json"


PUBLIC_CONFIG_FILE_PATH = "./entity.json"


def init_manager(public_config_path: str, private_config_path: str = None) -> EventBridge:
    return EventBridge.from_config_files(public_config_path, private_config_path)


def init_detected_event_from_file(file_path: str) -> DetectedEvent:
    with open(file_path, "r") as f:
        event_json = json.load(f)
    return DetectedEvent.from_dict(event_json)


def print_json_with_indent(data: dict):
    print(json.dumps(data, indent=4))


if __name__ == "__main__":
    manager = init_manager(PUBLIC_CONFIG_FILE_PATH)

    detected_event: DetectedEvent = init_detected_event_from_file(REQUESTED1_DETECTED_EVENT_JSON)
    print_json_with_indent(detected_event.to_dict())
    rbc_event = RbcEvent(detected_event, 0, manager)
    print_json_with_indent(rbc_event.decoded_json())
