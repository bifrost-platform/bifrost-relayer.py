from typing import Optional, List, Dict

from ..ethtype.account import EthAccount
from ..ethtype.amount import EthAmount
from ..ethtype.chaindata import EthReceipt
from ..ethtype.consts import ChainIndex
from ..ethtype.contract import EthContract
from ..ethtype.hexbytes import EthHashBytes, EthAddress, EthHexBytes
from ..ethtype.transaction import EthTransaction
from ..managers.eventhandler import DetectedEvent
from ..managers.ethchainmanager import EthChainManager
from ..managers.configs import EntityRootConfig, MultiChainConfig


class MultiChainManager:
    def __init__(self, root_config: EntityRootConfig):
        # entity info
        self.root_config = root_config
        self.__role = root_config.entity.role
        self.__active_account = EthAccount.from_secret(root_config.entity.secret_hex)

        # config for multichain entity
        self.__multichain_config = root_config.multichain_config

        # config for each chain
        self.__supported_chains = list()
        self.__chain_managers = dict()
        for chain_config in root_config.chains:
            chain_index = eval("ChainIndex." + chain_config.chain_name.upper())
            chain_manager = EthChainManager(chain_index, root_config)
            self.__supported_chains.append(chain_index)
            self.__chain_managers[chain_index] = chain_manager

    @property
    def role(self) -> str:
        return self.__role

    @property
    def active_account(self) -> EthAccount:
        return self.__active_account

    @property
    def supported_chain_list(self) -> list:
        return list(self.__chain_managers.keys())

    @property
    def multichain_config(self) -> MultiChainConfig:
        return self.__multichain_config

    def get_chain_manager_of(self, chain_index: ChainIndex) -> EthChainManager:
        return self.__chain_managers.get(chain_index)

    def get_contract_obj_on(self, chain_index: ChainIndex, contract_name: str) -> Optional[EthContract]:
        return self.get_chain_manager_of(chain_index).get_contract_by_name(contract_name)

    def world_call(self, chain_index: ChainIndex, contract_name: str, method_name: str, method_params: list):
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.call_transaction(contract_name, method_name, method_params)

    def world_build_transaction(self,
                                chain_index: ChainIndex,
                                contract_name: str,
                                method_name: str,
                                method_params: list, value: EthAmount = None) -> EthTransaction:
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.build_transaction(contract_name, method_name, method_params, value)

    def world_send_transaction(self,
                               chain_index: ChainIndex,
                               tx_with_fee: EthTransaction,
                               gas_limit_multiplier: float = 1.0) -> (EthTransaction, EthHashBytes):
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.send_transaction(tx_with_fee, gas_limit_multiplier=gas_limit_multiplier)

    def world_receipt_with_wait(
            self, chain_index: ChainIndex, tx_hash: EthHashBytes, matured: bool = True) -> EthReceipt:
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.eth_receipt_with_wait(tx_hash, matured)

    def world_receipt_without_wait(self, chain_index: ChainIndex, tx_hash: EthHashBytes) -> EthReceipt:
        chain_manager = self.get_chain_manager_of(chain_index)
        return chain_manager.eth_receipt_without_wait(tx_hash)

    def collect_unchecked_multichain_event_in_range(self, event_name: str, _range: Dict[ChainIndex, List[int]]):
        unchecked_events = list()
        for chain_index in self.__supported_chains:
            chain_manager = self.get_chain_manager_of(chain_index)
            from_block, to_block = _range[chain_index][0], _range[chain_index][1]
            unchecked_events += chain_manager.collect_target_event_in_range(event_name, from_block, to_block)
        return unchecked_events

    def collect_unchecked_multichain_events(self) -> List[DetectedEvent]:
        unchecked_events = list()
        for chain_index in self.__supported_chains:
            chain_manager = self.get_chain_manager_of(chain_index)
            unchecked_events += chain_manager.collect_unchecked_single_chain_events()
        return unchecked_events

    def decode_event(self, detected_event: DetectedEvent) -> tuple:
        contract_obj = self.get_contract_obj_on(detected_event.chain_index, detected_event.contract_name)
        return contract_obj.decode_event(detected_event.event_name, detected_event.data)

    def world_native_balance(self, chain_index: ChainIndex, addr: EthAddress = None) -> EthAmount:
        chain_manager = self.get_chain_manager_of(chain_index)

        if addr is None:
            addr = self.active_account.address
        return chain_manager.native_balance(addr)

    def world_transfer_coin(
            self, chain_index: ChainIndex, to_addr: EthAddress, value: EthAmount) -> (EthTransaction, EthHashBytes):
        chain_manager = self.get_chain_manager_of(chain_index)
        tx = chain_manager.build_tx(to_addr, EthHexBytes(0x00), value)
        return chain_manager.send_transaction(tx)
