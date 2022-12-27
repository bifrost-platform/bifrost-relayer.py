from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHashBytes
from chainpy.eth.ethtype.consts import ChainIndex
from chainpy.eth.managers.ethchainmanager import EthChainManager
from chainpy.eventbridge.eventbridge import EventBridge
from rbclib.consts import ConsensusOracleId, BridgeIndex, AggOracleId, ChainEventStatus


def find_height_by_timestamp(chain_manager: EthChainManager, target_time: int, front_height: int = 0,
                             front_time: int = 0):
    current_block = chain_manager.eth_get_block_by_height()
    current_height, current_time = current_block.number, current_block.timestamp  # as a rear

    if front_height < 1:
        front_height, front_time = chain_manager.latest_height, chain_manager.eth_get_block_by_height(
            chain_manager.latest_height).timestamp

    if front_time >= target_time:
        return front_height

    if chain_manager.chain_index != ChainIndex.BIFROST:
        target_time -= 30000
    return binary_search(chain_manager, front_height, front_time, current_height, current_time, target_time)


def binary_search(
        chain_manager: EthChainManager,
        front_height: int, front_time: int,
        rear_height: int, rear_time: int,
        target_time: int) -> int:
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


def is_selected_relayer(
        manager: EventBridge,
        target_chain: ChainIndex,
        addr: EthAddress,
        is_initial: bool = True) -> bool:
    return manager.world_call(target_chain, "relayer_authority", "is_selected_relayer", [addr.hex(), is_initial])[0]


# TODO how about integrate is_selected_relayer and is_selected_previous_relayer?
def is_selected_previous_relayer(
        manager: EventBridge,
        target_chain: ChainIndex,
        round_num: int,
        addr: EthAddress,
        is_initial: bool = True) -> bool:
    return manager.world_call(
        target_chain, "relayer_authority",
        "is_previous_selected_relayer", [round_num, addr.hex(), is_initial])[0]


def fetch_latest_round(manager: EventBridge, target_chain_index: ChainIndex) -> int:
    return manager.world_call(target_chain_index, "relayer_authority", "latest_round", [])[0]  # unzip


def fetch_round_info(manager: EventBridge) -> (int, int, int):
    resp = manager.world_call(ChainIndex.BIFROST, "authority", "round_info", [])
    current_rnd_idx, fir_session_idx, current_session_index = resp[:3]
    first_rnd_block, first_session_block, current_height, round_length, session_length = resp[3:]
    return current_height, current_rnd_idx, round_length


def fetch_sorted_relayer_list(manager: EventBridge, target_chain_index: ChainIndex, is_initial: bool = True) -> list:
    validator_tuple = manager.world_call(target_chain_index, "relayer_authority", "selected_relayers", [is_initial])[0]
    validator_list = list(validator_tuple)
    validator_list_lower = [addr.lower() for addr in validator_list]
    return sorted(validator_list_lower)


def fetch_sorted_previous_relayer_list(
        manager: EventBridge, target_chain_index: ChainIndex,
        rnd: int, is_initial: bool = True) -> list:
    validator_tuple = manager.world_call(target_chain_index, "relayer_authority", "previous_selected_relayers", [rnd, is_initial])[0]  # unzip
    validator_list = list(validator_tuple)
    validator_list_lower = [addr.lower() for addr in validator_list]
    return sorted(validator_list_lower)


def fetch_lowest_validator_round(manager: EventBridge) -> int:
    bottom_round = 2 ** 256 - 1
    for chain_index in manager.supported_chain_list:
        round_num = fetch_latest_round(manager, chain_index)
        if bottom_round > round_num:
            bottom_round = round_num
    return bottom_round


def fetch_relayer_num(manager: EventBridge, target_chain_index: ChainIndex, is_initial: bool = True) -> int:
    validator_tuple = fetch_sorted_relayer_list(manager, target_chain_index, is_initial)
    return len(validator_tuple)


def fetch_quorum(manager: EventBridge, target_chain_index: ChainIndex, rnd: int = None, is_initial: bool = True) -> int:
    if rnd is None:
        majority = manager.world_call(target_chain_index, "relayer_authority", "majority", [is_initial])[0]
    else:
        current_rnd = fetch_latest_round(manager, target_chain_index)
        if current_rnd - rnd > 6:
            majority = 0
        else:
            majority = manager.world_call(
                target_chain_index, "relayer_authority",
                "previous_majority", [rnd, is_initial])[0]
    return majority


def fetch_socket_rbc_sigs(manager: EventBridge, request_id: tuple, chain_event_status: ChainEventStatus):
    params = [request_id, int(chain_event_status.formatted_hex(), 16)]
    sigs = manager.world_call(ChainIndex.BIFROST, "socket", "get_signatures", params)
    return sigs[0]


def fetch_socket_vsp_sigs(manager: EventBridge, rnd: int):
    result = manager.world_call(ChainIndex.BIFROST, "socket", "get_round_signatures", [rnd])
    return result[0]


def fetch_oracle_latest_round(manager: EventBridge, oracle_id: ConsensusOracleId):
    oracle_id_bytes = oracle_id.formatted_bytes()
    return manager.world_call(ChainIndex.BIFROST, "oracle", "latest_oracle_round", [oracle_id_bytes])[0]


def fetch_price_from_oracle(manager: EventBridge, token: BridgeIndex) -> EthAmount:
    oid = AggOracleId.from_token_name(token.token_name())
    result = manager.world_call(ChainIndex.BIFROST, "oracle", "latest_oracle_data", [oid.formatted_bytes()])[0]

    if token == BridgeIndex.USDT_ETHEREUM or token == BridgeIndex.USDC_ETHEREUM:
        decimal = 6
    else:
        decimal = 18

    return EthAmount(result, decimal)


def fetch_btc_hash_from_oracle(manager: EventBridge) -> EthHashBytes:
    oid = ConsensusOracleId.BTC_HASH
    result = manager.world_call(ChainIndex.BIFROST, "oracle", "latest_oracle_data", [oid.formatted_bytes()])[0]
    return EthHashBytes(result)


def is_pulsed_hear_beat(manager: EventBridge) -> bool:
    """ Check if the relayer has ever sent a heartbeat transaction in this session."""
    relayer_addr = manager.active_account.address
    return manager.world_call(ChainIndex.BIFROST, "relayer_authority", "is_heartbeat_pulsed", [relayer_addr.hex()])[0]


# TODO why only ConsensusType?
def fetch_submitted_oracle_feed(
        manager: EventBridge,
        oracle_id: ConsensusOracleId,
        _round: int,
        validator_addr: EthAddress = None) -> EthHashBytes:
    if validator_addr is None:
        validator_addr = manager.active_account.address
    oracle_id_bytes = oracle_id.formatted_bytes()
    params = [oracle_id_bytes, validator_addr.hex(), _round]
    result = manager.world_call(ChainIndex.BIFROST, "oracle", "get_consensus_feed", params)[0]
    return EthHashBytes(result)


# TODO why only ConsensusType?
def is_submitted_oracle_feed(
        manager: EventBridge,
        oracle_id: ConsensusOracleId,
        _round: int,
        validator_addr: EthAddress = None) -> bool:
    """ Check whether the external data of the round has been transmitted. """
    result = fetch_submitted_oracle_feed(manager, oracle_id, _round, validator_addr)
    return result != 0
