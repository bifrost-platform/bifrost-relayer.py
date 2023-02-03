from time import sleep
from typing import List, Tuple

from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.chaindata import EthTransaction
from bridgeconst.consts import Chain, RBCMethodV1, Asset, RBCMethodDirection
from chainpy.eth.ethtype.hexbytes import EthHashBytes
from tools.utils import Manager
from relayer.user import User


class RequestParams:
    def __init__(self, target_chain: Chain, tx: EthTransaction, asset: Asset):
        self.chain = target_chain
        self.tx = tx
        self.asset = asset

    def __repr__(self) -> str:
        return "{}:{}".format(self.chain, self.asset.name)


def _build_request(user: Manager, dst_chain: Chain, asset: Asset, rbc_method: RBCMethodV1) -> RequestParams:
    direction = rbc_method.direction
    if direction == RBCMethodDirection.IN_AND_OUTBOUND or direction == RBCMethodDirection.NONE:
        raise Exception("Not supported direction: {}".format(direction.name))

    amount = EthAmount(0.02) if direction == RBCMethodDirection.INBOUND else EthAmount(0.01)
    amount = EthAmount(3.0, asset.decimal) if asset.decimal != 18 else amount

    tx = user.build_cross_action_tx(asset.chain, dst_chain, asset, rbc_method, amount)
    return RequestParams(asset.chain, tx, asset)


def build_request_batch(
        user: Manager, batch_num: int, dst_chain: Chain, asset: Asset, rbc_method: RBCMethodV1) -> List[RequestParams]:
    request_list = list()
    for _ in range(batch_num):
        action_data = _build_request(user, dst_chain, asset, rbc_method)
        request_list.append(action_data)
    return request_list


def send_request_batch(user: User, transactions: List[RequestParams]) -> List[Tuple[Chain, EthHashBytes]]:
    receipt_params = []
    for i, tx in enumerate(transactions):
        _, tx_hash = user.world_send_transaction(tx.chain, tx.tx)
        print(" - {}:{}".format(i, tx_hash.hex()))
        receipt_params.append((tx.chain, tx_hash))

    return receipt_params


def check_receipt_batch(user, receipt_params: List[Tuple[Chain, EthHashBytes]]):
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


def cccp_batch_send(user: Manager, batch_num: int, dst_chain: Chain, asset: Asset, rbc_method: RBCMethodV1):
    request_params = build_request_batch(user, batch_num, dst_chain, asset, rbc_method)
    print(">>> build transaction for each request")

    receipt_params = send_request_batch(user, request_params)
    print("\n>>> send transaction complete. check receipts after 30 secs")

    sleep(30)
    print(">>> start check receipts")
    check_receipt_batch(user, receipt_params)
