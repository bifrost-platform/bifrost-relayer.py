from typing import Optional, Any

from .exceptions import select_exception
from ..ethtype.account import EthAccount
from ..ethtype.hexbytes import EthHexBytes, EthHashBytes
from ..ethtype.consts import ChainIndex
from ..ethtype.amount import EthAmount
from ..ethtype.hexbytes import EthAddress

from .rpchandler import EthRpcClient
from .configs import FeeConfig, EntityRootConfig
from ..ethtype.transaction import EthTransaction


PRIORITY_FEE_MULTIPLIER = 4
TYPE0_GAS_MULTIPLIER = 1.5
TYPE2_GAS_MULTIPLIER = 2


class EthTxHandler(EthRpcClient):
    def __init__(self, chain_index: ChainIndex, root_config: EntityRootConfig):
        super().__init__(chain_index, root_config)

        chain_config = root_config.get_chain_config(chain_index)
        self.__fee_config = chain_config.tx_fee_type
        if self.__fee_config is None:
            # this will send transaction using network fee parameters
            self.__fee_config = FeeConfig.from_dict({"type": 0, "gas_price": 2 ** 255 - 1})

    @property
    def fee_config(self) -> FeeConfig:
        """
        The fee parameters read from the config file.
        This is used as the upper limit of fe when transaction is transmitted.
        """
        return self.__fee_config

    @property
    def tx_type(self) -> int:
        """ Type of transaction to be sent by tx-handler -1, 0, 1 and 2"""
        return self.__fee_config.type

    def build_tx(self,
                 to_addr: EthAddress,
                 data: EthHexBytes,
                 value: EthAmount = None,
                 sender_addr: EthAddress = None) -> EthTransaction:
        """ build basic transaction for call and send """
        return EthTransaction.init(self.chain_id, to_addr, value, data, sender_addr)

    def estimate_tx(self, transaction: EthTransaction, from_addr: EthAddress = None) -> int:
        """ estimate the transaction and return its gas limit"""
        tx_dict = transaction.call_dict()
        if from_addr is not None:
            tx_dict["from"] = from_addr.with_checksum()

        if "chainId" in tx_dict:
            del tx_dict["chainId"]

        try:
            return self.eth_estimate_gas(tx_dict)
        except Exception as e:
            select_exception(e)

    def call_tx(self, transaction: EthTransaction) -> Any:
        """ send call-transaction """
        try:
            return self.eth_call(transaction.call_dict())
        except Exception as e:
            select_exception(e)

    def fetch_network_fee_parameters(self) -> (Optional[int], Optional[int], Optional[int]):
        """ fetch fee parameters from the network """
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
                              tx: EthTransaction,
                              account: EthAccount,
                              boost: bool = False,
                              gas_limit_multiplier: float = 1.0) -> (bool, EthTransaction):
        # estimate, if necessary
        gas_limit = self.estimate_tx(tx, account.address)
        tx.set_gas_limit(int(gas_limit * gas_limit_multiplier))

        # fetch fee from network
        net_gas_price, net_base_fee_price, net_priority_fee_price = self.fetch_network_fee_parameters()

        if self.tx_type < 2:
            net_gas_price = int(net_gas_price * TYPE0_GAS_MULTIPLIER)
            if boost:
                net_gas_price = int(net_gas_price * 2.0)
            is_sendable = False if net_gas_price > self.fee_config.gas_price else True
            tx.set_gas_price(net_gas_price)
        else:
            net_priority_fee_price = int((net_priority_fee_price + 1) * PRIORITY_FEE_MULTIPLIER)
            if boost:
                net_base_fee_price = int(net_base_fee_price * 1.1)
                net_priority_fee_price = int(net_priority_fee_price * 1.1)
            net_max_gas_price = int((net_priority_fee_price + net_base_fee_price) * TYPE0_GAS_MULTIPLIER)

            is_sendable1 = True if net_priority_fee_price < self.fee_config.max_priority_price else False
            is_sendable2 = True if net_max_gas_price < self.fee_config.max_gas_price else False
            is_sendable = bool(is_sendable1 * is_sendable2)
            tx.set_gas_prices(net_max_gas_price, net_priority_fee_price)

        return is_sendable, tx

    def send_tx(self, tx: EthTransaction, account: EthAccount) -> EthHashBytes:
        if not tx.is_sendable():
            raise Exception("Check transaction parameters")
        signed_raw_tx = tx.sign_transaction(account)
        try:
            return self.eth_send_raw_transaction(signed_raw_tx)
        except Exception as e:
            select_exception(e)
