from time import sleep
from typing import List

from relayer.chainpy.eth.ethtype.amount import EthAmount
from relayer.chainpy.eth.ethtype.chaindata import EthTransaction
from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthHashBytes
from relayer.rbcevents.consts import TokenStreamIndex, RBCMethodIndex
from relayer.tools.consts import SUPPORTED_TOKEN_LIST, EXECUTABLE_TOKEN_LIST
from relayer.user import User


class ActionParams:
    def __init__(self, target_chain: ChainIndex, tx: EthTransaction, token_index: TokenStreamIndex):
        self.chain = target_chain
        self.tx = tx
        self.token_index = token_index

    def __repr__(self) -> str:
        return "{}:{}".format(self.chain, self.token_index.name)


class UsedTx:
    def __init__(self, target_chain: ChainIndex, tx_hash: EthHashBytes):
        self.chain = target_chain
        self.tx_hash = tx_hash

    def __repr__(self) -> str:
        return "{}:{}".format(self.chain, self.tx_hash.hex())


def _pre_build_tx(user: User, direction: str, token: TokenStreamIndex) -> ActionParams:
    if direction == "inbound":
        home_chain = token.home_chain_index()
        target_chain = ChainIndex.ETHEREUM if home_chain == ChainIndex.BIFROST else home_chain
    else:
        target_chain = ChainIndex.BIFROST

    if token == TokenStreamIndex.USDC_ETHEREUM or token == TokenStreamIndex.USDT_ETHEREUM:
        amount = EthAmount(3.0, 6)
    elif direction == "inbound":
        amount = EthAmount(0.02)
    else:
        amount = EthAmount(0.01)

    tx = user.build_cross_action_tx(target_chain, ChainIndex.BIFROST, token, RBCMethodIndex.WARP, amount)

    return ActionParams(target_chain, tx, token)


def batch_test(user: User, config: dict) -> List[ActionParams]:
    token_num = len(EXECUTABLE_TOKEN_LIST)
    iter_num = config["txNum"] // token_num
    remainder = config["txNum"] % token_num

    transactions = []
    for token in EXECUTABLE_TOKEN_LIST:
        for i in range(iter_num):
            action_data = _pre_build_tx(user, config["direction"], token)
            transactions.append(action_data)
    i = 0
    for token in EXECUTABLE_TOKEN_LIST:
        action_data = _pre_build_tx(user, config["direction"], token)
        transactions.append(action_data)
        i += 1
        if i == remainder:
            break
    return transactions


def send_transaction_batch(user: User, transactions: List[ActionParams]) -> List[UsedTx]:
    receipt_params = []
    for i, tx in enumerate(transactions):
        print(tx)
        try:
            _, tx_hash = user.world_send_transaction(tx.chain, tx.tx)
            print("nonce: ({}), fee({} {})".format(tx.tx.nonce, tx.tx.max_priority_fee_per_gas, tx.tx.max_fee_per_gas))
            used_tx = UsedTx(tx.chain, tx_hash)
            print(" - {}:{}".format(i, tx_hash.hex()))
            receipt_params.append(used_tx)
        except ReplaceTransactionUnderpriced as e:
            print("nonce: ({}), fee({} {})".format(tx.tx.nonce, tx.tx.max_priority_fee_per_gas, tx.tx.max_fee_per_gas))

    return receipt_params


def check_receipt_batch(user, used_txs: List[UsedTx]):
    for tx in used_txs:
        receipt = user.world_receipt_with_wait(tx.chain, tx.tx_hash)
        if receipt is None:
            print("tx without receipt: {}".format(tx.tx_hash.hex()))
            continue
        if receipt.status == 1:
            continue
        else:
            print("failed tx {}".format(tx.tx_hash.hex()))
            continue


def cccp_batch_send(user: User, config: dict):
    action_data_objs = batch_test(user, config)

    try:
        receipt_params = send_transaction_batch(user, action_data_objs)
    except KeyError as e:
        print(e)
        raise Exception(e)
    print(">>> send transaction complete.")

    print(">>> wait for 30 secs")
    sleep(30)
    print(">>> wake up! ")

    print(">>> start check receipts")
    check_receipt_batch(user, receipt_params)
