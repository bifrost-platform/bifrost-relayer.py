from typing import Tuple

from bridgeconst.consts import Chain, Symbol, RBCMethodV1, Asset
from chainpy.eth.ethtype.amount import EthAmount
from chainpy.eth.ethtype.hexbytes import EthAddress, EthHexBytes, EthHashBytes
from chainpy.eth.ethtype.receipt import EthReceipt
from chainpy.eth.ethtype.transaction import EthTransaction
from chainpy.eth.ethtype.utils import recursive_tuple_to_list
from chainpy.eth.managers.multichainmanager import MultiChainManager

from rbclib.primitives.relay_chain import chain_primitives
from relayer.user_utils import symbol_to_asset


class UserSubmit:
    """
    Data class for payload of user request (sent to the "First chain")
    """

    def __init__(
        self,
        method: RBCMethodV1,
        src_chain: Chain,
        dst_chain: Chain,
        symbol: Symbol,
        apply_addr: EthAddress,
        amount: EthAmount
    ):
        asset0, asset1 = symbol_to_asset(src_chain, symbol), symbol_to_asset(dst_chain, symbol)
        action_param_tuple = (
            asset0.formatted_bytes(),  # first token_index
            asset1.formatted_bytes(),
            apply_addr.with_checksum(),  # from address
            apply_addr.with_checksum(),  # to address
            amount.int(),
            EthHexBytes(b'\00')
        )

        inst_tuple = (dst_chain.formatted_bytes(), method.formatted_bytes())

        self.__data = (inst_tuple, action_param_tuple)

    def tuple(self) -> tuple:
        return self.__data


class User(MultiChainManager):
    def __init__(self, multichain_config: dict):
        super().__init__(multichain_config)

    def token_approve(
        self,
        chain: Chain,
        asset: Asset,
        target_addr: EthAddress,
        amount: EthAmount
    ) -> (EthTransaction, EthHashBytes):
        tx_with_fee = self.world_build_transaction(
            chain.name,
            asset.name,
            "approve",
            [target_addr.with_checksum(), amount.int()]
        )
        return self.world_send_transaction(chain.name, tx_with_fee)

    def world_get_allowance(
        self,
        chain: Chain,
        asset: Asset,
        spender: EthAddress,
        owner: EthAddress = None
    ):
        if owner is None:
            owner = self.active_account.address
        token_contract_name = asset.name
        allowance = self.world_call(chain.name, token_contract_name, "allowance", [owner, spender])
        return int.from_bytes(allowance, byteorder="big")

    def world_token_balance_of(
        self,
        chain: Chain,
        asset: Asset,
        target_addr: EthAddress = None
    ) -> EthAmount:
        target_addr = self.active_account.address if target_addr is None else target_addr
        value = self.world_call(
            chain.name,
            asset.name,
            "balanceOf",
            [target_addr.with_checksum()]
        )

        token_decimal = self.world_call(chain.name, asset.name, "decimals", [])[0]
        return EthAmount(value[0], token_decimal)

    def get_token_address(self, chain: Chain, asset: Asset) -> EthAddress:
        contract = self.get_contract_obj_on(chain.name, asset.name)
        return contract.address if contract is not None else EthAddress("0x00")

    def get_vault_addr(self, chain: Chain) -> EthAddress:
        contract = self.get_contract_obj_on(chain.name, "vault")
        return contract.address if contract is not None else None

    def get_socket_addr(self, chain: Chain) -> EthAddress:
        contract = self.get_contract_obj_on(chain.name, "socket")
        return contract.address if contract is not None else None

    def build_cross_action_tx(
        self,
        src_chain: Chain,
        dst_chain: Chain,
        symbol: Symbol,
        cross_action_index: RBCMethodV1,
        amount: EthAmount
    ) -> EthTransaction:
        user_request = UserSubmit(
            cross_action_index,
            src_chain, dst_chain,
            symbol,
            self.active_account.address,
            amount
        )

        value = amount if symbol_to_asset(src_chain, symbol).is_coin() else None

        return self.world_build_transaction(src_chain.name, "vault", "request", [user_request.tuple()], value)

    def send_cross_action(
        self,
        src_chain: Chain,
        dst_chain: Chain,
        symbol: Symbol,
        cross_action_index: RBCMethodV1,
        amount: EthAmount
    ) -> EthHashBytes:
        tx = self.build_cross_action_tx(src_chain, dst_chain, symbol, cross_action_index, amount)
        tx_hash = self.world_send_transaction(src_chain.name, tx)
        return tx_hash

    def send_cross_action_and_wait_receipt(
        self,
        src_chain: Chain,
        dst_chain: Chain,
        symbol: Symbol,
        cross_action_index: RBCMethodV1,
        amount: EthAmount
    ) -> Tuple[EthReceipt, Tuple[Chain, int, int]]:
        tx_hash = self.send_cross_action(src_chain, dst_chain, symbol, cross_action_index, amount)

        receipt = self.world_receipt_with_wait(src_chain.name, tx_hash, False)

        target_topic = EthHashBytes(0x918454f530580823dd0d8cf59cacb45a6eb7cc62f222d7129efba5821e77f191)
        log_data = receipt.get_log_data_by_topic(target_topic)

        result = self.get_contract_obj_on(src_chain.name, "socket"). \
            get_method_abi("Socket"). \
            decode_event_data(log_data)[0]
        return receipt, (Chain.from_bytes(result[0][0]), result[0][1], result[0][2])

    def build_rollback_params(
        self, chain: Chain, tx_hash: EthHashBytes
    ) -> Tuple[
        EthAddress,
        Tuple[
            Tuple[bytes, int, int],
            Tuple[Tuple[bytes, bytes], Tuple[bytes, bytes, str, str, int, bytes]]
        ]
    ]:
        chain_manager = self.get_chain_manager_of(chain.name)

        # find out request id
        receipt = chain_manager.eth_receipt_with_wait(tx_hash)
        result = self.get_contract_obj_on(chain.name, "socket"). \
            get_method_abi("Socket"). \
            decode_event_data(receipt.logs[2].data)[0]

        return EthAddress(result[3][2]), (result[0], (result[2], result[3]))

    def round_up(self, chain: Chain, is_initial: bool = True):
        current_bif_round = self.world_call(chain_primitives.BIFROST.name, "relayer_authority", "latest_round", [])[0]
        current_tar_round = self.world_call(chain.name, "relayer_authority", "latest_round", [])[0]

        if current_bif_round == current_tar_round + 1:
            validator_tuple = self.world_call(
                chain_primitives.BIFROST.name,
                "relayer_authority",
                "selected_relayers",
                [is_initial]
            )[0]

        elif current_bif_round > current_tar_round + 1:
            try:
                validator_tuple = self.world_call(
                    chain_primitives.BIFROST.name,
                    "relayer_authority",
                    "previous_selected_relayers",
                    [current_bif_round + 1, is_initial]
                )[0]
            except Exception as e:
                if str(e) == '[BFC_TEST] revert Tried to read round_index out of bounds':
                    validator_tuple = self.world_call(
                        chain_primitives.BIFROST.name,
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
            chain.name,
            "relayer_authority",
            "update_round",
            [current_tar_round + 1, sorted_validator_list]
        )

        return self.world_send_transaction(chain.name, pre_tx)
