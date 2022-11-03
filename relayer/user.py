from .chainpy.eth.ethtype.amount import EthAmount
from .chainpy.eth.ethtype.chaindata import EthReceipt
from .chainpy.eth.ethtype.consts import ChainIndex
from .chainpy.eth.ethtype.hexbytes import EthAddress, EthHexBytes, EthHashBytes
from .chainpy.eth.ethtype.transaction import EthTransaction
from .chainpy.eth.ethtype.utils import recursive_tuple_to_list
from .chainpy.eth.managers.multichainmanager import EntityRootConfig, MultiChainManager
from .rbcevents.consts import RBCMethodIndex, TokenStreamIndex


class UserSubmit:
    """
    Data class for payload of user request (sent to the "First chain")
    """
    def __init__(self,
                 method: RBCMethodIndex,
                 dst_chain_index: ChainIndex,
                 token_index0: TokenStreamIndex,
                 apply_addr: EthAddress,
                 amount: EthAmount):
        inst_tuple = (dst_chain_index.value, method.value)
        action_param_tuple = (
            token_index0.value,  # first token_index
            TokenStreamIndex.NONE.value,  # second token_index
            apply_addr.with_checksum(),  # from address
            apply_addr.with_checksum(),  # to address
            amount.int(),
            EthHexBytes(b'\00')
        )
        self.__data = (inst_tuple, action_param_tuple)

    def tuple(self) -> tuple:
        return self.__data


class User(MultiChainManager):
    def __init__(self, entity_config: EntityRootConfig):
        super().__init__(entity_config)

    def token_approve(self,
                      chain_index: ChainIndex,
                      token_index: TokenStreamIndex,
                      target_addr: EthAddress,
                      amount: EthAmount
                      ) -> (EthTransaction, EthHashBytes):
        tx_with_fee = self.world_build_transaction(
            chain_index,
            token_index.name,
            "approve",
            [target_addr.with_checksum(), amount.int()]
        )
        return self.world_send_transaction(chain_index, tx_with_fee)

    def world_get_allowance(self,
                            chain_index: ChainIndex,
                            token_name: str,
                            spender: EthAddress,
                            owner: EthAddress = None):
        if owner is None:
            owner = self.active_account.address
        token_contract_name = token_name
        allowance = self.world_call(chain_index, token_contract_name, "allowance", [owner, spender])
        return int.from_bytes(allowance, byteorder="big")

    def world_token_balance_of(self,
                               chain_idx: ChainIndex,
                               token_index: TokenStreamIndex,
                               target_addr: EthAddress = None) -> EthAmount:
        target_addr = self.active_account.address if target_addr is None else target_addr
        value = self.world_call(
            chain_idx,
            token_index.name,
            "balanceOf",
            [target_addr.with_checksum()]
        )

        token_decimal = self.world_call(
            chain_idx,
            token_index.name,
            "decimals",
            []
        )[0]

        return EthAmount(value[0], token_decimal)

    def get_token_address(self, chain_index: ChainIndex, token_name: str) -> EthAddress:
        contract = self.get_contract_obj_on(chain_index, token_name)
        return contract.address if contract is not None else EthAddress("0x00")

    def get_vault_addr(self, chain_index: ChainIndex) -> EthAddress:
        contract = self.get_contract_obj_on(chain_index, "vault")
        return contract.address if contract is not None else None

    def get_socket_addr(self, chain_index: ChainIndex) -> EthAddress:
        contract = self.get_contract_obj_on(chain_index, "socket")
        return contract.address if contract is not None else None

    def build_cross_action_tx(self,
                              src_chain: ChainIndex,
                              dst_chain: ChainIndex,
                              token_index: TokenStreamIndex,
                              cross_action_index: RBCMethodIndex,
                              amount: EthAmount) -> EthTransaction:
        user_request = UserSubmit(
            cross_action_index,
            dst_chain,
            token_index,
            self.active_account.address,
            amount
        )
        value = None
        if token_index.is_coin_on(src_chain):
            value = amount

        return self.world_build_transaction(src_chain, "vault", "request", [user_request.tuple()], value)

    def send_cross_action(self,
                          src_chain: ChainIndex,
                          dst_chain: ChainIndex,
                          token_index: TokenStreamIndex,
                          cross_action_index: RBCMethodIndex,
                          amount: EthAmount) -> EthHashBytes:
        tx = self.build_cross_action_tx(src_chain, dst_chain, token_index, cross_action_index, amount)
        _, tx_hash = self.world_send_transaction(src_chain, tx)
        return tx_hash

    def send_cross_action_and_wait_receipt(self,
                                           src_chain: ChainIndex,
                                           dst_chain: ChainIndex,
                                           token_index: TokenStreamIndex,
                                           cross_action_index: RBCMethodIndex,
                                           amount: EthAmount) -> EthReceipt:
        tx_hash = self.send_cross_action(src_chain, dst_chain, token_index, cross_action_index, amount)
        return self.world_receipt_with_wait(src_chain, tx_hash, False)

    def send_timeout_rollback(self, target_chain: ChainIndex, rnd: int, sequence_num: int) -> EthHashBytes:
        params = (target_chain.value, rnd, sequence_num)

        tx = self.world_build_transaction(
            target_chain,
            "socket",
            "timeout_rollback",
            [params]
        )
        tx, tx_hash = self.world_send_transaction(target_chain, tx)

        return tx_hash

    def round_up(self, chain_index: ChainIndex, validator_addr: EthAddress = None, is_initial: bool = True):
        current_validator_list = self.world_call(chain_index, "relayer_authority", "selected_relayers", [is_initial])[0]
        current_validator_list = recursive_tuple_to_list(current_validator_list)
        current_round = self.world_call(chain_index, "relayer_authority", "latest_round", [])[0]

        if validator_addr is not None:
            validator_idx = None
            for i, addr in enumerate(current_validator_list):
                if validator_addr == addr:
                    validator_idx = i
                    break

            if validator_idx is not None:
                del current_validator_list[validator_idx]
            else:
                current_validator_list.append(validator_addr.hex())

        current_validator_list = sorted(current_validator_list)
        pre_tx = self.world_build_transaction(
            chain_index,
            "relayer_authority",
            "update_round",
            [current_round + 1, current_validator_list]
        )

        sent_tx, tx_hash = self.world_send_transaction(chain_index, pre_tx)
        print("tx_hash: {}, nonce: {}".format(tx_hash.hex(), sent_tx.nonce))

        return tx_hash
