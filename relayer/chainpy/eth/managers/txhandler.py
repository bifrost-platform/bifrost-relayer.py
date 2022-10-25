import unittest
from typing import Union, Optional

from web3 import Web3  # TODO remove this dependency

from .exceptions import EstimateGasError, RpcEVMError
from ..ethtype.account import EthAccount
from ..ethtype.exceptions import EthUnderPriced, EthFeeCapError, EthTooLowPriority
from ..ethtype.hexbytes import EthHexBytes, EthHashBytes
from ..ethtype.transaction import TransactionType0, TransactionType2, CallTransaction
from ..ethtype.transaction import FeeParamsType0, FeeParamsType2
from ..ethtype.consts import ChainIndex
from ..ethtype.amount import EthAmount
from ..ethtype.hexbytes import EthAddress

from .rpchandler import EthRpcClient, rpc_logger
from .configs import FeeConfig, EntityRootConfig
from ...logger import formatted_log

CallTxUnion = Union[CallTransaction, TransactionType0, TransactionType2]
SendTxUnion = Union[TransactionType0, TransactionType2]

TxTypeOf = {0: TransactionType0, 2: TransactionType2}
FeeTypeOf = {0: FeeParamsType0, 2: FeeParamsType2}


class EthTxHandler(EthRpcClient):
    def __init__(self, chain_index: ChainIndex, root_config: EntityRootConfig):
        super().__init__(chain_index, root_config)

        chain_config = root_config.get_chain_config(chain_index)
        self.__w3 = Web3(Web3.HTTPProvider(chain_config.url_with_access_key))

        self.__fee_config = chain_config.tx_fee_type
        if self.__fee_config is None:
            # this will send transaction using network fee parameters
            self.__fee_config = FeeConfig.from_dict({"type": 0, "gas_price": 2 ** 255 - 1})

    @property
    def tx_type(self) -> int:
        return self.__fee_config.type

    def build_call_tx(self,
                      to_addr: EthAddress,
                      data: EthHexBytes,
                      value: EthAmount = None,
                      sender_addr: EthAddress = None) -> CallTransaction:
        return CallTransaction(self.chain_index, to_addr, data, value, sender_addr)

    def call_tx(self, transaction: CallTxUnion):
        if not isinstance(transaction, CallTransaction):
            raise Exception("Not allowed transaction type")

        return self.eth_call(transaction.dict())

    def build_tx_including_fee_upper_bound(self,
                                           to_addr: EthAddress,
                                           data: EthHexBytes,
                                           value: EthAmount = EthAmount("0x00")) -> Optional[SendTxUnion]:
        tx = TxTypeOf[self.tx_type](self.chain_id, to_addr, data, value)
        tx.fee_upper_bound = FeeTypeOf[self.tx_type](self.chain_index, self.__fee_config)
        return tx

    def estimate_tx(self, transaction: SendTxUnion, from_addr: EthAddress = None):
        if isinstance(transaction, CallTransaction):
            raise Exception("Not allowed transaction type")
        tx_dict = transaction.dict()
        if from_addr is not None:
            tx_dict["from"] = from_addr.with_checksum()

        if "chainId" in tx_dict:
            del tx_dict["chainId"]

        return self.eth_estimate_gas(tx_dict)

    def get_network_fee_parameters(self) -> (Optional[int], Optional[int], Optional[int]):
        gas_price, base_fee_price, priority_fee_price = None, None, None
        if self.tx_type == 0:
            gas_price = self.eth_get_gas_price()
        elif self.tx_type == 2:
            priority_fee_price = self.eth_get_priority_fee_per_gas()
            base_fee_price = self.eth_get_next_base_fee()
            if self.chain_index == ChainIndex.BIFROST:  # TODO bifrost specific config
                base_fee_price = max(base_fee_price, 1000 * 10 ** 9)
        else:
            raise Exception("Not supported fee type")
        return gas_price, base_fee_price, priority_fee_price

    def set_gas_limit_and_fee(self,
                              tx: SendTxUnion,
                              account: EthAccount,
                              boost: bool = False,
                              resend: bool = False,
                              gas_limit_multiplier: float = 1.0) -> (bool, SendTxUnion):
        # estimate, if necessary
        gas_limit = self.estimate_tx(tx, account.address)
        tx.gas_limit = int(gas_limit * gas_limit_multiplier)

        # fetch fee from network
        gas_price, base_fee_price, priority_fee_price = self.get_network_fee_parameters()

        # apply a boost option - set fee more than network fee
        if boost:
            if self.tx_type == 0:
                gas_price = int(gas_price * 2.0)
            if self.tx_type == 2:
                base_fee_price = int(base_fee_price * 1.1)
                priority_fee_price = int(priority_fee_price * 1.1)

        # apply a re-send option - allow fee more than limit (specified in config)
        if resend:
            tx.fee_upper_bound.increase_gas_fee_config()

        is_sendable = tx.fee_upper_bound.check_fee_upper_bound_and_commit_fee(gas_price, base_fee_price, priority_fee_price)
        return is_sendable, tx

    def send_tx(self, tx: SendTxUnion, account: EthAccount) -> EthHashBytes:
        if not tx.is_sendable():
            raise Exception("Check transaction parameters")

        # send transaction
        tx_dict = tx.dict()

        try:
            signed = self.__w3.eth.account.sign_transaction(tx_dict, account.priv)  # TODO convert rpc thing
            tx_hash = self.__w3.eth.send_raw_transaction(signed.rawTransaction)  # TODO convert rpc thing
            return EthHashBytes(tx_hash)
        except ValueError as e:
            code = e.args[0]["code"]
            msg = e.args[0]["message"]

            if code == -32003 and msg == "transaction underpriced":
                raise EthUnderPriced(msg)

            if code == -32000 and msg.startswith("tx fee ("):
                raise EthFeeCapError(msg)

            if code == -32603 and msg.startswith("submit transaction to pool failed: Pool(TooLowPriority { old"):
                raise EthTooLowPriority(msg)

            print(">>> {}|| nonce_from_net: {}, issued_by_myself: {}\nerror: {}".format(
                account.address.hex()[:10], self.eth_get_user_nonce(account.address), tx.nonce, e))

            formatted_log(
                rpc_logger,
                relayer_addr=None,
                log_id="SendTxError",
                related_chain=self.chain_index,
                log_data=msg
            )
