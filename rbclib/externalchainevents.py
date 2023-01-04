from typing import TYPE_CHECKING

from chainpy.eth.managers.eventobj import DetectedEvent
from rbclib.chainevents import RbcEvent, RBC_EVENT_STATUS_START_DATA_START_INDEX, RBC_EVENT_STATUS_START_DATA_END_INDEX, \
    ChainAcceptedEvent, ChainRejectedEvent  # do not remove!
from bridgeconst.consts import ChainEventStatus

if TYPE_CHECKING:
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
        if status == ChainEventStatus.ACCEPTED and status == ChainEventStatus.REJECTED:
            status_name = status.name.capitalize()
            casting_type = eval("Chain{}Event".format(status_name))
            return casting_type(detected_event, time_lock, relayer, True)
        else:
            return None
