from time import sleep
from typing import List, Tuple

from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.chaindata import EthTransaction
from chainpy.eth.ethtype.consts import ChainIndex
from chainpy.eth.ethtype.hexbytes import EthHashBytes
from rbclib.consts import TokenStreamIndex, RBCMethodIndex
from tools.consts import EXECUTABLE_TOKEN_LIST
from tools.utils import Manager, determine_decimal
from rbclib.user import User


class RequestParams:
    def __init__(self, target_chain: ChainIndex, tx: EthTransaction, token_index: TokenStreamIndex):
        self.chain = target_chain
        self.tx = tx
        self.token_index = token_index

    def __repr__(self) -> str:
        return "{}:{}".format(self.chain, self.token_index.name)


def _build_request(user: Manager, direction: str, token: TokenStreamIndex) -> RequestParams:
    decimal = determine_decimal(token)
    if direction == "inbound":
        home_chain = token.home_chain_index()
        target_chain = ChainIndex.ETHEREUM if home_chain == ChainIndex.BIFROST else home_chain
        amount = EthAmount(0.02)
    else:
        target_chain = ChainIndex.BIFROST
        amount = EthAmount(0.01)

    if decimal != 18:
        amount = EthAmount(3.0, decimal)

    tx = user.build_cross_action_tx(target_chain, ChainIndex.BIFROST, token, RBCMethodIndex.WARP, amount)
    return RequestParams(target_chain, tx, token)


def build_request_batch(user: Manager, config: dict) -> List[RequestParams]:
    request_num = config["txNum"]
    i = 0

    request_list = list()
    while True:
        for token in EXECUTABLE_TOKEN_LIST:
            action_data = _build_request(user, config["direction"], token)
            request_list.append(action_data)
            i += 1
            if i == request_num:
                break
        if i == request_num:
            break

    return request_list


def send_request_batch(user: User, transactions: List[RequestParams]) -> List[Tuple[ChainIndex, EthHashBytes]]:
    receipt_params = []
    for i, tx in enumerate(transactions):
        _, tx_hash = user.world_send_transaction(tx.chain, tx.tx)
        print(" - {}:{}".format(i, tx_hash.hex()))
        receipt_params.append((tx.chain, tx_hash))

    return receipt_params


def check_receipt_batch(user, receipt_params: List[Tuple[ChainIndex, EthHashBytes]]):
    for receipt_param in receipt_params:
        chain, tx_hash = receipt_param[0], receipt_param[1]
        receipt = user.world_receipt_with_wait(chain, tx_hash)
        if receipt is None:
            print("tx without receipt: {}".format(tx_hash))
            continue
        if receipt.status == 1:
            continue
        else:
            print("failed tx {}".format(tx_hash))
            continue


def cccp_batch_send(user: Manager, config: dict):
    request_params = build_request_batch(user, config)
    print(">>> build transaction for each request")

    receipt_params = send_request_batch(user, request_params)
    print("\n>>> send transaction complete. check receipts after 30 secs")

    sleep(30)
    print(">>> start check receipts")
    check_receipt_batch(user, receipt_params)
