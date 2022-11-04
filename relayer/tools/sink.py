from time import sleep
from typing import List

from relayer.chainpy.eth.ethtype.account import EthAccount
from relayer.chainpy.eth.ethtype.amount import EthAmount
from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthAddress
from relayer.chainpy.eth.managers.configs import EntityRootConfig
from relayer.chainpy.eth.managers.ethchainmanager import EthChainManager

key_pairs = [
    ('0x3ff539eecc7511878029a88ff20d90b38ab2aa79eb9b8b71ef2b80da180ff008', '0xa43274bf8a9805c837e8fabca855dda970040025'),
    ('0x40f37a055d547cb895a1753d0750293ba48f1813f051c526924a70bf2031f6de', '0x8363df05c74ae4b922cc4165b1c397ed9a6a42c6'),
    ('0xff13e46c5e968ceef4bbfb3c862004ee24a0bc5cb2d4d0ba47cd650da0bdfe58', '0x8b9b86e78d40d6730f503330917bb6d5fb154e4d'),
    ('0x3953e0b81908ed5399de3aaf1c33990c37348cf74fb25547325e4397386ed416', '0xcd9cea54132236560719ff4ca4384cd7da7461fb'),
    ('0x44e5e4abbe1d61d0155cce30622ed139e5b3dd63dd94a38869c2241b3c710720', '0xe75e98b84b5f58e62441579a242bf978c4eae418'),
    ('0xc1801c5842a58a3cf6caf04a18b3b5573905d95a8b6f5ba382c6957a92f88495', '0x7b449658f988cb506e339bd85a866ebbcdfa0225'),
    ('0x8b626d5ff7a439b91237a042dc27122e1e3aebc1b2d8c35782daf350e7ba25cb', '0xe13400a2c97b5681680dea71f64d672ed394aa07'),
    ('0xf57bce3e9e11139e01c328306ff55fd0f1244b3f450becb78a1d89bb7e1c8a79', '0x1535094226394909769799bf013979d4668b30b8'),
    ('0x56a15d220dccd912feae989d6be785f7b41b560222512e9a297d8d8d551ecc3e', '0x06adaffaf5f541265ef8710945f508200e851b50'),
    ('0x7a9e289c295e0b2e9c5ea77849e0e8e08f77106e20798be76eb067989def8c14', '0xa9250b7760e85a09bb15624efca4aa9a5ea59029'),
    ('0x315ef284f3273db6fe487a34c9ba30d99b26a77dcea3d7b488110ddfeaa64da0', '0x53a5ef3a9e8baea3894b17cb983e46c249617132'),
    ('0x6f7636264d0b512e31f168b959a05aadf7a2741e14ea5fe040d260640c3479c0', '0xe08bfcdc6946c92c3de07eab244e2453e7c86bff'),
    ('0x33f7e853cc944d2973eb350c211f0b7575459e7f52ee2007b7f35fa9e45eb600', '0xb0e5c7cfdb698eee9aa59a93fd38e8015681287b'),
    ('0x7d50e95b24f7b7230efe3907505630470425a3d929eaca8be2bc0fd6f2e82c07', '0x6cbe3014ef04db25498ad810ad0324aa4b012b9d'),
    ('0x572f90cda49d19483da8c0198071bae9ae628d4bdd1531a0f4138d163bf3453', '0x3ce97d05e4f1fcd5bdfc22fd6fbc99b1287f6bd9'),
    ('0x7fd66889826012c6d6a126af0118a943102207ef510a1b4205c779a3724dc148', '0x350ecf2fcc6de3513b6962c2c9e37d42d274d98e'),
    ('0xa6af39e8ef71b9c8f99f9e916a585c06684842a00bda5087894ccb9fba4ffe1c', '0x471871fae127d7e1838c7084719292046fe28b2c'),
    ('0x276826d31e08e42ca279892660862e3464d0f0ea9cb12c5d49496c66937c64f1', '0xf70f4f30355ad1f1c8d0715fda13369242ef8156'),
    ('0x56b552098837b76f1883b80677c221daef2d98e03bc7e1a9008fbc33e94a95cb', '0x2d275b8df5e74c7be1370c4d6a9890766a737a41'),
    ('0x26d0d5896702bcb7fc124cad027514abe72fc99040c36fffb944aae1bd94384d', '0x441523e73dfa53f5b2ea320677bfe2b5d69f2975')
]


ACCOUNT_NUM = len(key_pairs)


def init_managers() -> List[EthChainManager]:
    manager_config = {
        "entity": {
            "role": "User",
            "account_name": "user",
            "secret_hex": "",
            "supporting_chains": ["POLYGON"]
        },
        "polygon": {
            "chain_name": "POLYGON",
            "block_period_sec": 5,
            "url_with_access_key": "https://polygon-mumbai.chain.thebifrost.io"
        }
    }

    managers = list()
    for i in range(ACCOUNT_NUM):
        manager_config["entity"]["secret_hex"] = key_pairs[i][0]
        manager = EthChainManager(ChainIndex.POLYGON, EntityRootConfig.from_dict(manager_config))
        print("address: {}".format(manager.account.address.hex()))
        managers.append(manager)

    return managers


def generate_accounts(num: int):
    accounts = list()
    for i in range(num):
        account = EthAccount.generate()
        accounts.append(account)
    print([(hex(account.priv), account.address.hex()) for account in accounts])


def sink(managers: List[EthChainManager]):
    receiver_addr = EthAddress("0x466D25b791FD4882e15aF01FC28a633014104B2b")
    criteria_amount = EthAmount("0.01")

    while True:
        for manager in managers:
            balance = manager.native_balance()
            if balance > criteria_amount:
                print("catch token!")
                sending_amount = balance - criteria_amount
                _, tx_hash = manager.transfer_native_coin(receiver_addr, sending_amount)
                receipt = manager.eth_receipt_with_wait(tx_hash, False)
                assert receipt.status == 1
                print("send token!")
        sleep(3)


if __name__ == "__main__":
    sink(init_managers())
