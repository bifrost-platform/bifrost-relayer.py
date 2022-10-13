from typing import List, Optional

from ..ethtype.consts import ChainIndex
from ..ethtype.contract import EthContract
from ..ethtype.exceptions import RpcExceedRequestTime
from ..ethtype.hexbytes import EthAddress, EthHashBytes

from .eventobj import DetectedEvent
from .configs import EntityRootConfig
from .rpchandler import EthRpcClient


class EthEventHandler(EthRpcClient):
    def __init__(self, chain_index: ChainIndex, root_config: EntityRootConfig):
        super().__init__(chain_index, root_config)
        chain_config = root_config.get_chain_config(chain_index)

        if chain_config.events is None or chain_config.events == []:
            self.events = []
            self.__matured_latest_height = 0
            return
        self.events = chain_config.events

        self.__matured_latest_height = chain_config.bootstrap_latest_height
        self.__max_log_num = chain_config.max_log_num

        self.__contract_by_event_name = dict()
        for event in self.events:
            # parse contract's address and abi
            event_contract_obj: Optional[EthContract] = None
            for contract_config in chain_config.contracts:
                if contract_config.name == event.contract_name:
                    event_contract_obj = EthContract.from_abi_file(
                        contract_config.name,
                        contract_config.address,
                        root_config.project_root_path + contract_config.abi_path)
                    break

            if event_contract_obj is not None:
                self.__contract_by_event_name[event.event_name] = event_contract_obj

        self.__event_name_by_topic = dict()
        for event_name, contract in self.__contract_by_event_name.items():
            topic = contract.get_method_abi(event_name).get_topic()
            self.__event_name_by_topic[topic.hex()] = event_name

    def _get_emitter_addresses(self) -> list:
        addresses = list()
        for event_name, contract in self.__contract_by_event_name.items():
            addresses.append(contract.address)
        return addresses

    def _get_event_topics(self) -> list:
        topics = list()
        for event_name, contract in self.__contract_by_event_name.items():
            topic = contract.get_method_abi(event_name).get_topic()
            topics.append(topic)
        return topics

    def _get_event_name_by_topic(self, topic: EthHashBytes) -> str:
        return self.__event_name_by_topic[topic.hex()]

    def _get_contract_name_by_event_name(self, event_name: str) -> str:
        contract_obj = self.__contract_by_event_name[event_name]
        return contract_obj.contract_name

    def _collect_target_event_in_range(self, event_name: str, from_block: int, to_block: int) -> List[DetectedEvent]:
        if to_block < from_block:
            return list()

        emitter = self.__contract_by_event_name.get(event_name)
        if emitter is None:
            return list()
        emitter_addr = emitter.address
        event_topic = emitter.get_method_abi(event_name).get_topic()

        try:
            raw_logs = self.eth_get_logs(from_block, to_block, [emitter_addr], [event_topic])
        except RpcExceedRequestTime:
            self.__max_log_num = self.__max_log_num // 2
            delta_half = (to_block - from_block) // 2
            detected_events = self._collect_target_event_in_range(event_name, from_block, from_block + delta_half)
            detected_events += self._collect_target_event_in_range(event_name, from_block + delta_half + 1, to_block)
            return detected_events

        historical_logs = list()
        for raw_log in raw_logs:
            # loads information related to the log
            topic, contract_address = EthHashBytes(raw_log.topics[0]), EthAddress(raw_log.address)
            event_name = self._get_event_name_by_topic(topic)
            contract_name = self._get_contract_name_by_event_name(event_name)

            # check weather the log was emitted by one of target contracts
            if emitter_addr != contract_address:
                raise Exception("Topic and Contract address in the event are not matched.")
            # build event object and collect it (to return)
            detected_event = DetectedEvent(self.chain_index, contract_name, event_name, raw_log)
            historical_logs.append(detected_event)

        return historical_logs

    def collect_target_event_in_range(self,
                                      event_name: str,
                                      from_block: int,
                                      to_block: int = None) -> List[DetectedEvent]:
        """  collect the event in specific range (at the single blockchain) """
        to_block = self.eth_get_matured_block_number() if to_block is None else to_block

        if to_block < from_block:
            return list()

        delta_blocks = to_block - from_block
        loop_num = delta_blocks // self.__max_log_num
        if delta_blocks % self.__max_log_num != 0:
            loop_num += 1

        historical_logs = list()
        prev_height = from_block
        for i in range(loop_num):
            next_height = min(prev_height + self.__max_log_num, to_block)
            historical_logs += self._collect_target_event_in_range(event_name, prev_height, next_height)
            if next_height == to_block:
                break
            prev_height = next_height + 1
        return historical_logs

    def collect_unchecked_single_chain_events(self) -> List[DetectedEvent]:
        """ collect every type of events until the current block (at the single blockchain) """
        previous_matured_max_height = self.latest_height
        current_matured_max_height = self.eth_get_matured_block_number()
        if current_matured_max_height <= previous_matured_max_height:
            return list()

        historical_events = list()
        for event_name in self.__contract_by_event_name.keys():
            historical_events += self.collect_target_event_in_range(
                event_name,
                previous_matured_max_height,
                current_matured_max_height
            )
        self.latest_height = current_matured_max_height + 1

        return historical_events

    @property
    def latest_height(self) -> int:
        return self.__matured_latest_height

    @latest_height.setter
    def latest_height(self, height: int):
        self.__matured_latest_height = height
