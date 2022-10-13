import json

from relayer.chainpy.eth.ethtype.amount import EthAmount
from relayer.chainpy.eth.ethtype.consts import ChainIndex


def test_manager_init(ganache_eth_chain_manager):
    assert ganache_eth_chain_manager.chain_index == ChainIndex.ETHEREUM
    assert ganache_eth_chain_manager.chain_id == 0x539
    assert ganache_eth_chain_manager.account.address == "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1"  # ganache default
    assert ganache_eth_chain_manager.latest_height == 0
    assert ganache_eth_chain_manager.url == "http://127.0.0.1:8545"
    assert ganache_eth_chain_manager.tx_type == 0


def test_send_tx(ganache_eth_chain_manager, receiver_address):
    # caching balances
    sending_value = EthAmount(0.01)
    prev_sender_balance = ganache_eth_chain_manager.native_balance()
    prev_receiver_balance = ganache_eth_chain_manager.native_balance(receiver_address)

    # transfer coin
    tx, tx_hash = ganache_eth_chain_manager.transfer_native_coin(receiver_address, sending_value)
    # check receipt
    receipt = ganache_eth_chain_manager.eth_receipt_with_wait(tx_hash, False)
    if receipt.status == 1:
        after_sender_balance = ganache_eth_chain_manager.native_balance()
        after_receiver_balance = ganache_eth_chain_manager.native_balance(receiver_address)
        assert prev_sender_balance - sending_value > after_sender_balance
        assert prev_receiver_balance + sending_value == after_receiver_balance


class TransactionData:
    def __init__(self, i, tx, tx_hash):
        self.i = i
        self.tx = tx
        self.tx_hash = tx_hash


# it may fail
def test_batch_send_tx(ganache_eth_chain_manager, receiver_address):
    sending_value = EthAmount(0.01)

    tx_data_set = list()
    for i in range(50):
        tx, tx_hash = ganache_eth_chain_manager.transfer_native_coin(receiver_address, sending_value)

        tx_data_set.append(TransactionData(i, tx, tx_hash))
        print("send {}-th tx..".format(i))
    print("tx_hashes = {}".format(json.dumps([tx_data.tx_hash.hex() + "  # {}-th".format(tx_data.i) for tx_data in tx_data_set], indent=4)))

    for tx_data in tx_data_set:
        receipt = ganache_eth_chain_manager.eth_receipt_with_wait(tx_data.tx_hash, False)
        assert receipt.status == 1
        print("check {}-th tx..".format(tx_data.i))
