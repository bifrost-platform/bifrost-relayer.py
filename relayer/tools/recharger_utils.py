from time import sleep
from typing import List, Optional

import requests

from relayer.chainpy.eth.ethtype.chaindata import EthBlock
from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthAddress, EthHexBytes
from relayer.chainpy.eth.managers.ethchainmanager import EthChainManager
from relayer.tools.consts import SCORE_SERVER_URL, BIFNET_LIMIT_AMOUNT, EXTERNAL_LIMIT_AMOUNT, CONTROLLER_TO_DISCORD_ID, \
    RELAYER_ONCE
from relayer.tools.utils import remove_duplicated_addr, display_coins_balances, RelayerInfo, get_controller_of
from relayer.user import User


class ScoreClient:
    @staticmethod
    def fetch_relayers_with_version() -> List[RelayerInfo]:
        """ Fetch relayer addresses from the score server. and return addresses w/ duplicated"""
        response_json = requests.get(SCORE_SERVER_URL).json()

        ret = list()
        addr_cache = list()
        for result in response_json["relayers"]:
            if result["_id"] == "0x0":
                continue
            addr_cache.append(EthAddress(result["_id"]))
            ret.append(RelayerInfo.from_resp(result))

        for addr in RELAYER_ONCE:
            addr_obj = EthAddress(addr)
            if addr_obj not in addr_cache:
                ret.append(RelayerInfo(addr_obj, 0))

        return ret

    @staticmethod
    def recharge_coins(user: User, addrs: List[EthAddress]):
        receipt_params = list()
        i = 0
        for addr in addrs:
            for chain_index in user.supported_chain_list:
                # determine the limit amount
                limit_amount = BIFNET_LIMIT_AMOUNT if chain_index == ChainIndex.BIFROST else EXTERNAL_LIMIT_AMOUNT

                # fetch a balance of the relayer
                relayer_balance = user.world_native_balance(chain_index, addr=addr)
                if relayer_balance < limit_amount:
                    # send coins to the relayer

                    recharge_amount = limit_amount - relayer_balance
                    chain_manager = user.get_chain_manager_of(chain_index)
                    tx = chain_manager.build_tx(addr, EthHexBytes(0x00), recharge_amount)
                    _, tx_hash = chain_manager.send_transaction(tx)
                    receipt_params.append((chain_index, tx_hash, recharge_amount))

                    print("{:2} sent {} coins to {} with txHash({}) nonce({})".format(
                        i, chain_index, addr.hex(), tx_hash.hex(), tx.nonce))
                    i += 1
                    # check receipt and display the result

        for i, receipt_param in enumerate(receipt_params):
            target_chain = receipt_param[0]
            tx_hash = receipt_param[1]
            amount = receipt_param[2]
            receipt = user.world_receipt_with_wait(target_chain, tx_hash, False)
            if receipt is None:
                print("{:2} no-receipt recharge balance: {} recharged({})".format(
                    i, target_chain, amount))
            elif receipt.status == 0:
                print("{:2} fail recharge balance: {} recharged({})".format(
                    i, target_chain, amount))
            else:
                print("{:2} success recharge balance: {} recharged({})".format(
                    i, target_chain, amount))


def _fetch_blocks(chain_manager: EthChainManager, from_height: int, to_height: int):
    base_height = from_height
    num_block = to_height - from_height + 1

    fetched_block = list()
    for i in range(num_block):
        block = chain_manager.eth_get_block_by_height(base_height + i, True)
        fetched_block.append(block)
    return fetched_block


def _parse_active_addr_in_block(block: EthBlock) -> List[EthAddress]:
    function_selector = EthHexBytes(0x433671f8)
    target_addr = list()
    for tx in block.transactions:
        if tx.input.hex().startswith(function_selector.hex()):
            target_addr.append(tx.sender)
    return target_addr


def _parse_active_addr_in_blocks(chain_manager: EthChainManager, from_height: int, to_height: int):
    blocks = _fetch_blocks(chain_manager, from_height, to_height)
    active_addrs = list()
    for block in blocks:
        if block.number == 228584:
            print("here")
        addrs = _parse_active_addr_in_block(block)
        active_addrs += addrs
    return remove_duplicated_addr(active_addrs)


def get_discord_id_by_controller(controller: EthAddress) -> Optional[str]:
    controller_hex = controller.hex()
    for i, key in enumerate(CONTROLLER_TO_DISCORD_ID.keys()):
        if key.lower() == controller_hex:
            return CONTROLLER_TO_DISCORD_ID[key]
    return None


# Tool
def is_registered_relayer(user, addr: EthAddress) -> bool:
    try:
        _ = get_controller_of(user, addr)
        return True
    except Exception:
        return False


# Tool
def fetch_healthy_relayers(admin: User, history_block_num: int = 40) -> List[EthAddress]:
    chain_manager = admin.get_chain_manager_of(ChainIndex.BIFROST)

    # determine searching range
    start_block_num = chain_manager.eth_get_latest_block_number() - history_block_num
    end_block_num = chain_manager.eth_get_latest_block_number()

    return _parse_active_addr_in_blocks(chain_manager, start_block_num, end_block_num)


# Tool
def fetch_once_relayers() -> List[RelayerInfo]:
    return ScoreClient.fetch_relayers_with_version()


# Tool - Action
def recharge_coin(user: User, addrs: List[EthAddress], cmd: int = 3):
    """ cmd - 1: display admin balance, 2: recharge once, 3: recharge forever"""
    display_coins_balances(user)
    if cmd == 2 or cmd == 3:
        while True:
            ScoreClient.recharge_coins(user, addrs)
            if cmd == 2:
                break
            sleep(120)
            print("sleep 120 sec")
    else:
        raise Exception("Invalid cmd")
