from typing import List

from relayer.chainpy.eth.ethtype.chaindata import EthBlock, EthTransaction
from relayer.chainpy.eth.ethtype.dataclassmeta import hex_to_int
from relayer.chainpy.eth.ethtype.hexbytes import EthHashBytes


def check_block_basic(fixture: dict, block: EthBlock, expected_verbose: bool, expected_block_type: int):
    assert block.verbose == expected_verbose
    assert block.type == expected_block_type
    if block.type == 2:
        assert block.base_fee_per_gas is not None

    assert block.difficulty == hex_to_int(fixture["difficulty"])
    assert block.extra_data == fixture["extraData"]
    assert block.gas_limit == hex_to_int(fixture["gasLimit"])
    assert block.hash == fixture["hash"]
    assert block.logs_bloom == fixture["logsBloom"]
    assert block.miner == fixture["miner"]
    assert block.number == hex_to_int(fixture["number"])
    assert block.parent_hash == fixture["parentHash"]
    assert block.receipts_root == fixture["receiptsRoot"]
    assert block.sha3_uncles == fixture["sha3Uncles"]
    assert block.size == hex_to_int(fixture["size"])
    assert block.timestamp == hex_to_int(fixture["timestamp"])
    assert block.total_difficulty == hex_to_int(fixture["totalDifficulty"])
    assert block.transactions_root == fixture["transactionsRoot"]
    # assert block.transactions == fixture["total_difficulty"]
    assert block.uncles == fixture["uncles"]
    nonce = fixture.get("nonce")
    assert block.nonce == (0 if nonce is None else hex_to_int(fixture["nonce"]))
    mix_hash = fixture.get("mixHash")
    assert block.mix_hash == EthHashBytes.zero() if mix_hash is None else mix_hash

    if block.type == 2:
        assert block.base_fee_per_gas == hex_to_int(fixture["baseFeePerGas"])
    else:
        assert block.base_fee_per_gas is None  # TODO test


def check_transaction_basic(fixture: dict, txs: List[EthTransaction], expected_verbosity: bool):
    for i, tx in enumerate(txs):
        # check params
        actual_verbosity = tx.block_hash != EthHashBytes.zero()
        assert actual_verbosity == expected_verbosity

        assert isinstance(tx, EthTransaction)

        fixture_target_tx = fixture["transactions"][i]
        if not expected_verbosity:
            assert tx.hash == fixture_target_tx
        else:
            assert tx.hash == fixture_target_tx["hash"]
            assert tx.block_hash == fixture_target_tx["blockHash"]
            assert tx.block_number == hex_to_int(fixture_target_tx["blockNumber"])
            assert tx.sender == fixture_target_tx["from"]
            assert tx.gas == hex_to_int(fixture_target_tx["gas"])
            assert tx.gas_price == hex_to_int(fixture_target_tx["gasPrice"])
            assert tx.input == fixture_target_tx["input"]
            assert tx.nonce == hex_to_int(fixture_target_tx["nonce"])
            assert tx.r == hex_to_int(fixture_target_tx["r"])
            assert tx.s == hex_to_int(fixture_target_tx["s"])
            assert tx.v == hex_to_int(fixture_target_tx["v"])
            assert tx.transaction_index == hex_to_int(fixture_target_tx["transactionIndex"])
            assert tx.value == hex_to_int(fixture_target_tx["value"])
            assert tx.to == fixture_target_tx["to"]

            chain_id = fixture_target_tx.get("chainId")
            assert tx.chain_id == (hex_to_int(chain_id) if chain_id is not None else 0)

            expected_type = 0 if tx.max_fee_per_gas == 0 else 2
            if expected_type == 2:
                assert tx.access_list == fixture_target_tx["accessList"]
                assert tx.max_fee_per_gas == hex_to_int(fixture_target_tx["maxFeePerGas"])
                assert tx.max_priority_fee_per_gas == hex_to_int(fixture_target_tx["maxPriorityFeePerGas"])
            else:
                assert tx.access_list == []
                assert tx.max_fee_per_gas == 0
                assert tx.max_priority_fee_per_gas == 0


def test_fetch_block_and_transaction(
        bifrost_block_verbosity_true,
        bifrost_block_verbosity_false,
        goerli_block_verbosity_true,
        goerli_block_verbosity_false,
        polygon_block_verbosity_true,
        polygon_block_verbosity_false,
        bnb_block_verbosity_true,
        bnb_block_verbosity_false):
    bifrost_true: EthBlock = EthBlock.from_dict(bifrost_block_verbosity_true)
    check_block_basic(bifrost_block_verbosity_true, bifrost_true, True, 2)
    check_transaction_basic(bifrost_block_verbosity_true, bifrost_true.transactions, True)

    bifrost_false = EthBlock.from_dict(bifrost_block_verbosity_false)
    check_block_basic(bifrost_block_verbosity_false, bifrost_false, False, 2)
    check_transaction_basic(bifrost_block_verbosity_false, bifrost_false.transactions, False)

    goerli_true = EthBlock.from_dict(goerli_block_verbosity_true)
    check_block_basic(goerli_block_verbosity_true, goerli_true, True, 2)
    check_transaction_basic(goerli_block_verbosity_true, goerli_true.transactions, True)

    goerli_false = EthBlock.from_dict(goerli_block_verbosity_false)
    check_block_basic(goerli_block_verbosity_false, goerli_false, False, 2)
    check_transaction_basic(goerli_block_verbosity_false, goerli_false.transactions, False)

    polygon_true = EthBlock.from_dict(polygon_block_verbosity_true)
    check_block_basic(polygon_block_verbosity_true, polygon_true, True, 2)
    check_transaction_basic(polygon_block_verbosity_true, polygon_true.transactions, True)

    polygon_false = EthBlock.from_dict(polygon_block_verbosity_false)
    check_block_basic(polygon_block_verbosity_false, polygon_false, False, 2)
    check_transaction_basic(polygon_block_verbosity_false, polygon_false.transactions, False)

    bnb_true = EthBlock.from_dict(bnb_block_verbosity_true)
    check_block_basic(bnb_block_verbosity_true, bnb_true, True, 0)
    check_transaction_basic(bnb_block_verbosity_true, bnb_true.transactions, True)

    bnb_false = EthBlock.from_dict(bnb_block_verbosity_false)
    check_block_basic(bnb_block_verbosity_false, bnb_false, False, 0)
    check_transaction_basic(bnb_block_verbosity_false, bnb_false.transactions, False)


# def test_fetch_receipt_and_log():
