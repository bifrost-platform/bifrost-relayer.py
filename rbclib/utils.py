import inspect
from typing import Optional

from bridgeconst.consts import Chain
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHashBytes
from chainpy.eth.managers.ethchainmanager import EthChainManager
from chainpy.eventbridge.eventbridge import EventBridge
from chainpy.logger import global_logger

from primitives.enums import ChainEventStatus, Oracle
from rbclib.primitives.enums import chain_enum


def log_invalid_flow(log_id: str, event):
    caller_func_name = inspect.stack()[1].function
    global_logger.debug(log_id, "InvalidFlow: {} called when handling {} by {}".format(
        caller_func_name,
        event.summary(),
        event.manager.active_account.address
    ))


def find_height_by_timestamp(chain_manager: EthChainManager, target_time: int, front_height: int = 0, front_time: int = 0):
    current_block = chain_manager.eth_get_block_by_height()
    current_height, current_time = current_block.number, current_block.timestamp  # as a rear

    if front_height < 1:
        front_height, front_time = chain_manager.latest_height, chain_manager.eth_get_block_by_height(
            chain_manager.latest_height).timestamp

    if front_time >= target_time:
        return front_height

    if Chain[chain_manager.chain_name] != chain_enum.BIFROST:
        target_time -= 30000
    return binary_search(chain_manager, front_height, front_time, current_height, current_time, target_time)


def binary_search(
    chain_manager: EthChainManager, front_height: int, front_time: int, rear_height: int, rear_time: int, target_time: int
) -> int:
    if front_time > rear_time or front_height > rear_height:
        raise Exception("binary search prams error: front > rear")

    medium_height = (front_height + rear_height) // 2
    medium_block = chain_manager.eth_get_block_by_height(medium_height)
    if abs(target_time - medium_block.timestamp) < 30000:  # 30 secs
        return medium_height
    elif target_time > medium_block.timestamp:
        return binary_search(
            chain_manager,
            medium_height, medium_block.timestamp,
            rear_height, rear_time,
            target_time
        )
    else:
        return binary_search(
            chain_manager,
            front_height, front_time,
            medium_height, medium_block.timestamp,
            target_time
        )


def fetch_latest_round(manager: EventBridge, target_chain: Chain) -> int:
    return manager.world_call(target_chain.name, "relayer_authority", "latest_round", [])[0]  # unzip


def fetch_bottom_round(manager: EventBridge) -> int:
    bottom_round = 2 ** 256 - 1
    for chain_name in manager.supported_chain_list:
        chain = Chain[chain_name]
        round_num = fetch_latest_round(manager, chain)
        if bottom_round > round_num:
            bottom_round = round_num
    return bottom_round


def fetch_round_info(manager: EventBridge) -> (int, int, int):
    resp = manager.world_call(chain_enum.BIFROST.name, "authority", "round_info", [])
    current_rnd_idx, fir_session_idx, current_session_index = resp[:3]
    first_rnd_block, first_session_block, current_height, round_length, session_length = resp[3:]
    return current_height, current_rnd_idx, round_length


def is_selected_relayer(
    manager: EventBridge, chain: Chain, rnd: int = None, relayer_address: EthAddress = None, is_initial: bool = True
) -> bool:
    method = "is_selected_relayer" if rnd is None else "is_previous_selected_relayer"
    params = [relayer_address.hex(), is_initial] if rnd is None else [rnd, relayer_address.hex(), is_initial]

    return manager.world_call(chain.name, "relayer_authority", method, params)[0]


def fetch_relayer_index(
    manager: EventBridge, chain: Chain, rnd: int = None, relayer_address: EthAddress = None
) -> Optional[int]:
    """ if rnd is None"""
    sorted_relayer_list = fetch_sorted_relayer_list_lower(manager, chain, rnd, is_initial=True)
    relayer_address = manager.active_account.address.hex().lower() \
        if relayer_address is None else relayer_address.hex().lower()

    try:
        return sorted_relayer_list.index(relayer_address)
    except ValueError:
        return None


def fetch_sorted_relayer_list_lower(
    manager: EventBridge, chain: Chain, rnd: int = None, is_initial: bool = True
) -> list:
    method = "selected_relayers" if rnd is None else "previous_selected_relayers"
    params = [is_initial] if rnd is None else [rnd, is_initial]

    validator_tuple = manager.world_call(chain.name, "relayer_authority", method, params)[0]
    validator_list = list(validator_tuple)
    validator_list_lower = [addr.lower() for addr in validator_list]
    return sorted(validator_list_lower)


def fetch_relayer_num(manager: EventBridge, target_chain: Chain, is_initial: bool = True) -> int:
    validator_tuple = fetch_sorted_relayer_list_lower(manager, target_chain, is_initial=is_initial)
    return len(validator_tuple)


def fetch_quorum(manager: EventBridge, target_chain: Chain, rnd: int = None, is_initial: bool = True) -> int:
    method = "majority" if rnd is None else "previous_majority"
    params = [is_initial] if rnd is None else [rnd, is_initial]
    return manager.world_call(target_chain.name, "relayer_authority", method, params)[0]


def fetch_socket_rbc_sigs(manager: EventBridge, request_id: tuple, chain_event_status: ChainEventStatus):
    params = [request_id, int(chain_event_status.formatted_hex(), 16)]
    sigs = manager.world_call(chain_enum.BIFROST.name, "socket", "get_signatures", params)
    return sigs[0]


def fetch_socket_vsp_sigs(manager: EventBridge, rnd: int):
    result = manager.world_call(chain_enum.BIFROST.name, "socket", "get_round_signatures", [rnd])
    return result[0]


def fetch_oracle_latest_round(manager: EventBridge, oracle_id: Oracle):
    return manager.world_call(chain_enum.BIFROST.name, "oracle", "latest_oracle_round", [oracle_id.value])[0]


def is_heart_beat_pulsed(manager: EventBridge) -> bool:
    """ Check if the relayer has ever sent a heartbeat transaction in this session."""
    relayer_addr = manager.active_account.address
    return manager.world_call(
        chain_enum.BIFROST.name, "relayer_authority", "is_heartbeat_pulsed", [relayer_addr.hex()]
    )[0]


def is_submitted_oracle_feed(
    manager: EventBridge, oracle: Oracle, rnd: int, relayer_address: EthAddress = None
) -> bool:
    """ Check whether the external data of the round has been transmitted. Only use in btc hash up """
    relayer_address = manager.active_account.address if relayer_address is None else relayer_address

    params = [oracle.value, relayer_address.hex(), rnd]
    result = manager.world_call(chain_enum.BIFROST.name, "oracle", "get_consensus_feed", params)[0]
    return EthHashBytes(result) != 0


def sort_by_event_status(arr):  # : arr: List["RbcEvent"], return: : List["RbcEvent"]
    ret_arr = list()
    for element in arr:
        ret_arr.append((element.status.value, element))
    return [item_tuple[1] for item_tuple in sorted(ret_arr)]


def extract_latest_event_status(arr):  # arr: List["RbcEvent"]
    sorted_list = sort_by_event_status(arr)
    status_list = [element.status for element in sorted_list]

    inbound = sorted_list[0].is_inbound()
    if inbound:
        return sorted_list[-1]
    else:
        if ChainEventStatus.COMMITTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.COMMITTED)]
        elif ChainEventStatus.ROLLBACKED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.ROLLBACKED)]
        elif ChainEventStatus.EXECUTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.EXECUTED)]
        elif ChainEventStatus.REVERTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.REVERTED)]
        elif ChainEventStatus.ACCEPTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.ACCEPTED)]
        elif ChainEventStatus.REJECTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.REJECTED)]
        elif ChainEventStatus.REQUESTED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.REQUESTED)]
        elif ChainEventStatus.FAILED in status_list:
            return sorted_list[status_list.index(ChainEventStatus.REQUESTED)]
        else:
            raise Exception("Invalid event status")
