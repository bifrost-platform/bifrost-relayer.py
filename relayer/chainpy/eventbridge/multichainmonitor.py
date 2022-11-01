import logging
from queue import PriorityQueue
from typing import Union
import time

from relayer.chainpy.eventbridge.chaineventabc import ChainEventABC
from relayer.chainpy.eventbridge.periodiceventabc import PeriodicEventABC
from relayer.chainpy.eventbridge.utils import timestamp_msec
from relayer.chainpy.eth.managers.configs import EntityRootConfig
from relayer.chainpy.eth.managers.multichainmanager import MultiChainManager
from relayer.chainpy.logger import Logger, formatted_log


queue_logger = Logger("EventQueue", logging.INFO)
bootstrap_logger = Logger("Bootstrap", logging.INFO)
monitor_logger = Logger("Monitor", logging.INFO)


class TimePriorityQueue:
    """
    Time-Priority Queue (Variant of Queue) that retrieves open items in time priority order (the soonest first).
     - time of item in the Queue, means "Time lock" which indicates when the item can be used.

    Methods
    @ enqueue(event); event must have "time_lock" member.
    @ pop_matured_item() -> Pop an item with a time lock earlier than the current time. (or block process)

    """
    STAY_PERIOD_SEC = 180  # 3 minutes

    def __init__(self, max_size: int = -1):
        self.__queue = PriorityQueue(maxsize=max_size)

    def enqueue(self, event: Union[ChainEventABC, PeriodicEventABC]):
        # do nothing for a none event
        if event is None:
            return None

        # do nothing for event with invalid time lock
        if event.time_lock < 0:
            return None

        # check event types
        if not isinstance(event, ChainEventABC) and not isinstance(event, PeriodicEventABC):
            raise Exception(
                "Only allowed \"ChainEventABC\" or \"PeriodicEventABC\" types, but actual {}".format(type(event))
            )

        # enqueue item with time lock
        self.__queue.put((event.time_lock, event))

    def pop(self) -> Union[ChainEventABC, PeriodicEventABC, None]:
        """ Pop the item with the soonest time lock, or block this process until the queue is not empty. """
        return self.__queue.get()[1]

    def is_empty(self) -> bool:
        return self.__queue.empty()

    def qsize(self) -> int:
        return self.__queue.qsize()

    def pop_matured_event(self):
        """ Pop an item with a time lock earlier than the current time. (or block process) """
        item: Union[ChainEventABC, PeriodicEventABC] = self.pop()
        if timestamp_msec() >= item.time_lock:
            return item

        # re-enqueue if the item is not matured.
        self.enqueue(item)
        remaining_time = item.time_lock - timestamp_msec()
        queue_logger.debug("the soonest item will matured after {} secs".format(remaining_time // 1000))
        time.sleep(1)
        return None


class MultiChainMonitor(MultiChainManager):
    def __init__(self, entity_config: EntityRootConfig):
        super().__init__(entity_config)
        self.__queue = TimePriorityQueue()
        self.__events_types = dict()  # event_name to event_type
        self.__offchain_source_types = dict()

    @property
    def queue(self) -> TimePriorityQueue:
        return self.__queue

    def register_chain_event_obj(self, event_name: str, event_type: type):
        if not issubclass(event_type, ChainEventABC):
            raise Exception("event type to be registered must subclass of EventABC")
        if event_name in self.__events_types.keys():
            raise Exception("Already existing type: {}".format(event_type))
        self.__events_types[event_name] = event_type

    def register_offchain_event_obj(self, source_id: str, source_type: type):
        if not issubclass(source_type, PeriodicEventABC):
            raise Exception("oracle source type to be registered must subclass of EventABC")
        if source_id in self.__offchain_source_types.keys():
            raise Exception("Already existing type: {}".format(source_type))
        self.__offchain_source_types[source_id] = source_type

    def _generate_periodic_offchain_task(self):
        for source_id, source_type in self.__offchain_source_types.items():
            source_obj = source_type(self)
            self.__queue.enqueue(source_obj)

    def bootstrap_chain_events(self):
        heights = dict()
        for chain_index in self.supported_chain_list:
            chain_manager = self.get_chain_manager_of(chain_index)
            current_block_height = chain_manager.eth_get_matured_block_number()
            heights[chain_index] = [chain_manager.latest_height, current_block_height]
            chain_manager.latest_height = current_block_height

        for event_name, event_class in self.__events_types.items():
            not_handled_event_objs = event_class.bootstrap(self, heights)
            if not not_handled_event_objs:
                continue
            for not_handled_event_obj in not_handled_event_objs:
                self.__queue.enqueue(not_handled_event_obj)
        return True

    def run_world_chain_monitor(self):
        """
        A runner to find the designated event from blockchains. Whenever detecting the event, enqueue it.
        """
        while True:
            detected_events = self.collect_unchecked_multichain_events()
            for detected_event in detected_events:
                event_name = detected_event.event_name
                event_type = self.__events_types[event_name]

                chain_event = event_type.init(detected_event, timestamp_msec(), self)
                self.__queue.enqueue(chain_event)

                formatted_log(
                    monitor_logger,
                    relayer_addr=self.active_account.address,
                    log_id=chain_event.summary(),
                    related_chain=chain_event.on_chain,
                    log_data="Detected"
                )
            time.sleep(self.multichain_config.chain_monitor_period_sec)
