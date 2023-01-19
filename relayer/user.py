from bridgeconst.consts import Chain
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.chaindata import EthReceipt
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHexBytes, EthHashBytes
from chainpy.eth.ethtype.transaction import EthTransaction
from chainpy.eth.ethtype.utils import recursive_tuple_to_list
from chainpy.eth.managers.multichainmanager import MultiChainManager
from bridgeconst.consts import RBCMethodV1, Asset

from rbclib.switchable_enum import SwitchableChain


class UserSubmit:
    """
    Data class for payload of user request (sent to the "First chain")
    """
    def __init__(self,
                 method: RBCMethodV1,
                 dst_chain: Chain,
                 asset0: Asset,
                 apply_addr: EthAddress,
                 amount: EthAmount):
        inst_tuple = (dst_chain.formatted_bytes(), method.formatted_bytes())

        action_param_tuple = (
            asset0.formatted_bytes(),  # first token_index
            Asset.NONE.formatted_bytes(),  # second token_index
            apply_addr.with_checksum(),  # from address
            apply_addr.with_checksum(),  # to address
            amount.int(),
            EthHexBytes(b'\00')
        )
        self.__data = (inst_tuple, action_param_tuple)

    def tuple(self) -> tuple:
        return self.__data


class User(MultiChainManager):
    def __init__(self, multichain_config: dict):
        super().__init__(multichain_config)

    def token_approve(self,
                      chain: Chain,
                      asset: Asset,
                      target_addr: EthAddress,
                      amount: EthAmount
                      ) -> (EthTransaction, EthHashBytes):
        tx_with_fee = self.world_build_transaction(
            chain,
            asset.name,
            "approve",
            [target_addr.with_checksum(), amount.int()]
        )
        return self.world_send_transaction(chain, tx_with_fee)

    def world_get_allowance(self,
                            chain: Chain,
                            asset: Asset,
                            spender: EthAddress,
                            owner: EthAddress = None):
        if owner is None:
            owner = self.active_account.address
        token_contract_name = asset.name
        allowance = self.world_call(chain, token_contract_name, "allowance", [owner, spender])
        return int.from_bytes(allowance, byteorder="big")

    def world_token_balance_of(self,
                               chain: Chain,
                               asset: Asset,
                               target_addr: EthAddress = None) -> EthAmount:
        target_addr = self.active_account.address if target_addr is None else target_addr
        value = self.world_call(
            chain,
            asset.name,
            "balanceOf",
            [target_addr.with_checksum()]
        )

        token_decimal = self.world_call(chain, asset.name, "decimals", [])[0]
        return EthAmount(value[0], token_decimal)

    def get_token_address(self, chain_index: Chain, asset: Asset) -> EthAddress:
        contract = self.get_contract_obj_on(chain_index, asset.name)
        return contract.address if contract is not None else EthAddress("0x00")

    def get_vault_addr(self, chain: Chain) -> EthAddress:
        contract = self.get_contract_obj_on(chain, "vault")
        return contract.address if contract is not None else None

    def get_socket_addr(self, chain: Chain) -> EthAddress:
        contract = self.get_contract_obj_on(chain, "socket")
        return contract.address if contract is not None else None

    def build_cross_action_tx(self,
                              src_chain: Chain,
                              dst_chain: Chain,
                              asset: Asset,
                              cross_action_index: RBCMethodV1,
                              amount: EthAmount) -> EthTransaction:
        user_request = UserSubmit(
            cross_action_index,
            dst_chain,
            asset,
            self.active_account.address,
            amount
        )
        value = None
        if asset.is_coin():
            value = amount

        return self.world_build_transaction(src_chain, "vault", "request", [user_request.tuple()], value)

    def send_cross_action(self,
                          src_chain: Chain,
                          dst_chain: Chain,
                          asset: Asset,
                          cross_action_index: RBCMethodV1,
                          amount: EthAmount) -> EthHashBytes:
        tx = self.build_cross_action_tx(src_chain, dst_chain, asset, cross_action_index, amount)
        tx_hash = self.world_send_transaction(src_chain, tx)
        return tx_hash

    def send_cross_action_and_wait_receipt(self,
                                           src_chain: Chain,
                                           dst_chain: Chain,
                                           asset: Asset,
                                           cross_action_index: RBCMethodV1,
                                           amount: EthAmount) -> EthReceipt:
        tx_hash = self.send_cross_action(src_chain, dst_chain, asset, cross_action_index, amount)
        return self.world_receipt_with_wait(src_chain, tx_hash, False)

    def send_timeout_rollback(self, target_chain: Chain, rnd: int, sequence_num: int) -> EthHashBytes:
        params = (target_chain.value, rnd, sequence_num)

        tx = self.world_build_transaction(
            target_chain,
            "socket",
            "timeout_rollback",
            [params]
        )
        tx, tx_hash = self.world_send_transaction(target_chain, tx)

        return tx_hash

    def round_up(self, chain: Chain, is_initial: bool = True):
        current_bif_round = self.world_call(SwitchableChain.BIFROST, "relayer_authority", "latest_round", [])[0]
        current_tar_round = self.world_call(chain, "relayer_authority", "latest_round", [])[0]

        if current_bif_round == current_tar_round + 1:
            validator_tuple = self.world_call(
                SwitchableChain.BIFROST,
                "relayer_authority",
                "selected_relayers",
                [is_initial]
            )[0]

        elif current_bif_round > current_tar_round + 1:
            try:
                validator_tuple = self.world_call(
                    SwitchableChain.BIFROST,
                    "relayer_authority",
                    "previous_selected_relayers",
                    [current_bif_round + 1, is_initial]
                )[0]
            except Exception as e:
                if str(e) == 'Not handled error: evm error: Other("Out of round index")':
                    validator_tuple = self.world_call(
                        SwitchableChain.BIFROST,
                        "relayer_authority",
                        "selected_relayers",
                        [is_initial]
                    )[0]
                else:
                    raise Exception("Not handled error")
        else:
            raise Exception("Wrong validator sync")

        validator_list = recursive_tuple_to_list(validator_tuple)
        sorted_validator_list = sorted(validator_list)

        pre_tx = self.world_build_transaction(
            chain,
            "relayer_authority",
            "update_round",
            [current_tar_round + 1, sorted_validator_list]
        )

        sent_tx, tx_hash = self.world_send_transaction(chain, pre_tx)
        print("tx_hash: {}, nonce: {}".format(tx_hash.hex(), sent_tx.nonce))

        return tx_hash
