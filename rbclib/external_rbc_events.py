from bridgeconst.consts import ChainEventStatus
from chainpy.eth.managers.eventobj import DetectedEvent

from rbclib.chainevents import RbcEvent, RBC_EVENT_STATUS_START_DATA_START_INDEX, RBC_EVENT_STATUS_START_DATA_END_INDEX
from relayer.relayer import Relayer


class ExternalRbcEvents(RbcEvent):
    def __init__(self, detected_event: DetectedEvent, time_lock: int, manager: "Relayer"):
        super().__init__(detected_event, time_lock, manager)

    @classmethod
    def init(cls, detected_event: DetectedEvent, time_lock: int, relayer: "Relayer"):
        """ Depending on the event status, selects a child class of Socket Event, and initiates its instance. """
        # parse event-status from event data (fast, but not expandable)
        status_data = detected_event.data[RBC_EVENT_STATUS_START_DATA_START_INDEX:RBC_EVENT_STATUS_START_DATA_END_INDEX]
        status = ChainEventStatus(status_data.int())

        if status == ChainEventStatus.ACCEPTED \
                or status == ChainEventStatus.REJECTED \
                or status == ChainEventStatus.COMMITTED \
                or status == ChainEventStatus.ROLLBACKED:
            casting_type = RbcEvent.select_child(status)
            return casting_type(detected_event, time_lock, relayer)
        else:
            return None
