import os
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey, EllipticCurvePublicKey

from ecdsa import ecdsa
from ecdsa.ellipticcurve import PointJacobi
from ecdsa.keys import SigningKey, VerifyingKey
from ecdsa.curves import Curve, SECP256k1
from cryptography.hazmat.primitives.asymmetric import ec

from .hexbytes import EthAddress, EthHexBytes, EthHashBytes
from .utils import *


def convert_singing_key_obj(ecdsa_signing_key: SigningKey) -> EllipticCurvePrivateKey:
    private_key = EthHexBytes(ecdsa_signing_key.to_string())
    return ec.derive_private_key(private_key.int(), ec.SECP256K1())


def convert_verifying_key_obj(ecdsa_verifying_key: VerifyingKey) -> EllipticCurvePublicKey:
    encoded_verifying_key = ecdsa_verifying_key.to_string()
    return EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), encoded_verifying_key)


def password_as_bytes(password: Union[str, int, bytes] = None):
    if password is None:
        return None
    if isinstance(password, str):
        return password.encode()
    elif isinstance(password, bytes):
        return password
    elif isinstance(password, int):
        return password.to_bytes(32, byteorder="big")
    else:
        raise Exception("Not supported password type")


class WrappedVerifyingKey(VerifyingKey):
    def __init__(self, curve: Curve, hash_func, pubkey):
        super().__init__(_error__please_use_generate=True)
        self.curve = curve
        self.default_hashfunc = hash_func
        self.pubkey = pubkey

    @classmethod
    def from_verifying_key(cls, verifying_key: VerifyingKey):
        string = verifying_key.to_string()
        curve = verifying_key.curve
        hash_func = verifying_key.default_hashfunc
        point = PointJacobi.from_bytes(
            curve.curve,
            string,
            validate_encoding=True,
            valid_encodings=None,
        )
        pubkey = ecdsa.Public_key(curve.generator, point, True)
        pubkey.order = curve.order
        return cls(curve, hash_func, pubkey)

    def hex(self) -> str:
        vk_bytes = self.to_string()
        return vk_bytes.hex()

    def bytes(self) -> bytes:
        return self.to_string()

    def coordinates(self) -> (int, int):
        vk_hex = self.hex().replace("0x", "")
        return int(vk_hex[:64], 16), int(vk_hex[64:], 16)

    def ecdsa_verify_msg(self, r: EthHexBytes, s: EthHexBytes, msg: EthHexBytes) -> bool:
        return super().verify(r + s, msg)

    def ecdsa_verify_hash(self, r: EthHexBytes, s: EthHexBytes, msg_digest: EthHashBytes):
        return super().verify_digest(r + s, msg_digest)


class WrappedSignature:
    def __init__(self, r: EthHexBytes, s: EthHexBytes, v: Optional[int]):
        if len(r) != 32 or len(s) != 32:
            raise Exception("Signature size error: r(), s()".format(len(r), len(r)))
        self.__r: EthHexBytes = r
        self.__s: EthHexBytes = s
        self.__v: int = v

    @classmethod
    def from_sig_ints(cls, r: int, s: int, v: int = None):
        return cls(EthHexBytes(r, 32), EthHexBytes(s, 32), v)

    def encoded_bytes(self) -> EthHexBytes:
        return self.__r + self.__s

    @property
    def r(self) -> int:
        return self.__r.int()

    @property
    def s(self) -> int:
        return self.__s.int()

    @property
    def v(self) -> int:
        return self.__v

    def rs(self) -> (int, int):
        return self.__r.int(), self.__s.int()

    def rsv(self) -> (int, int, int):
        if self.__v is None:
            raise Exception("v is none")
        return self.__r.int(), self.__s.int(), self.__v


class EthAccount:
    def __init__(self, signing_key: SigningKey, curve: 'Curve' = SECP256k1):
        self.__signing_key_obj: SigningKey = signing_key
        self.__curve = curve
        self.__verifying_key_obj = None
        self.__address = None

    @classmethod
    def generate(cls, curve: "Curve" = SECP256k1):
        private_bytes = SigningKey.generate(curve=curve, hashfunc=ETH_HASH)
        return cls(private_bytes, curve)

    @classmethod
    def from_secret(cls, secret: Union[bytearray, bytes, int, str], curve: "Curve" = SECP256k1, hash_fn=ETH_HASH):
        private_int = EthHexBytes(secret).int()
        signing_key = SigningKey.from_secret_exponent(private_int, curve=curve, hashfunc=hash_fn)
        return cls(signing_key, curve)

    @classmethod
    def from_private_key_pem(cls,
                             pem_bytes: bytes,
                             password: Union[str, bytes, int] = None,
                             curve: "Curve" = SECP256k1,
                             hash_fn=ETH_HASH):
        password = password_as_bytes(password)
        ecc_private_key = serialization.load_pem_private_key(pem_bytes, password=password, backend=default_backend())
        private_key_int = ecc_private_key.private_numbers().private_value
        return cls.from_secret(private_key_int, curve, hash_fn)

    def priv_to_pem(self, password: Union[str, bytes, int] = None) -> bytes:
        password = password_as_bytes(password)

        enc_algo = serialization.NoEncryption() if password is None else serialization.BestAvailableEncryption(password)
        pem_signing_key = convert_singing_key_obj(self.__signing_key_obj)

        return pem_signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=enc_algo
        )

    @property
    def priv(self) -> int:
        return int.from_bytes(self.__signing_key_obj.to_string(), byteorder="big")

    @property
    def vk(self) -> WrappedVerifyingKey:
        if self.__verifying_key_obj is None:
            self.__verifying_key_obj = WrappedVerifyingKey.from_verifying_key(self.__signing_key_obj.verifying_key)
        return self.__verifying_key_obj

    def vk_to_pem(self):
        return self.vk.to_pem()

    @property
    def address(self) -> EthAddress:
        if self.__address is None:
            hash_ = ETH_HASH(self.vk.bytes()).digest()
            self.__address = EthAddress(hash_[-20:].hex())
        return self.__address

    def ecdsa_sign(self, msg: bytes) -> WrappedSignature:
        msg_digest = ETH_HASH(msg).digest()
        return self.ecdsa_sign_on_digest(msg_digest)

    def ecdsa_sign_on_digest(self, msg_digest: bytes) -> WrappedSignature:
        sig = self.__signing_key_obj.sign_digest(msg_digest)
        return WrappedSignature(EthHexBytes(sig[:32]), EthHexBytes(sig[32:]), None)

    @staticmethod
    def ecdsa_verify_by_msg(msg: bytes, r: int, s: int, verifying_key_obj: WrappedVerifyingKey) -> bool:
        msg_digest = ETH_HASH(msg).digest()
        return EthAccount.ecdsa_verify_by_digest(msg_digest, r, s, verifying_key_obj)

    @staticmethod
    def ecdsa_verify_by_digest(msg_digest: bytes, r: int, s: int, verifying_key_obj: WrappedVerifyingKey) -> bool:
        digest_obj, r_obj, s_obj = EthHashBytes(msg_digest), EthHexBytes(r, 32), EthHexBytes(s, 32)
        return verifying_key_obj.verify_digest(r_obj + s_obj, digest_obj)

    def ecdsa_recoverable_sign(self, msg: bytes, chain_id: int = None) -> WrappedSignature:
        msg_digest = ETH_HASH(msg).digest()
        return self.ecdsa_recoverable_sign_on_digest(msg_digest, chain_id)

    def ecdsa_recoverable_sign_on_digest(self, msg_digest: bytes, chain_id: int = None):
        k: int = int.from_bytes(os.urandom(32), byteorder="big")

        sig = self.__signing_key_obj.sign_digest(msg_digest, k=k)
        criteria = int((self.__curve.generator * k).y())
        v = 1 if criteria % 2 else 0

        return WrappedSignature(EthHexBytes(sig[:32]), EthHexBytes(sig[32:]), to_eth_v(v, chain_id))

    @classmethod
    def ecdsa_recover_address(cls, r: int, s: int, v: int, msg: bytes, curve=SECP256k1) -> EthAddress:
        msg_digest = ETH_HASH(msg).digest()
        return EthAccount.ecdsa_recover_address_with_digest(r, s, v, EthHashBytes(msg_digest), curve)

    @classmethod
    def ecdsa_recover_address_with_digest(cls,
                                          r: int, s: int, v: int,
                                          msg_digest: bytes, curve=SECP256k1) -> EthAddress:
        sig_bytes = (EthHexBytes(r, 32) + EthHexBytes(s, 32)).bytes()

        # issue: python type-checker discovers a warning on this line.
        # cause: VerifyingKey.from_public_key_recovery_with_digest is class method, but returns list of VerifyingKeys.
        pubkey_candidates = VerifyingKey.from_public_key_recovery_with_digest(
            sig_bytes,
            msg_digest,
            curve,
            sigdecode=lambda sig, gen: (
                int.from_bytes(sig[:32], byteorder="big"),
                int.from_bytes(sig[32:], byteorder="big")
            ),
            allow_truncate=True
        )

        vk_index = 1 if v % 2 == 0 else 0
        pubkey_obj = pubkey_candidates[vk_index]
        pubkey_hash = ETH_HASH(pubkey_obj.to_string()).digest()
        return EthAddress(pubkey_hash[-20:].hex())


class TestEthAccount(unittest.TestCase):
    def setUp(self) -> None:
        self.test_private = 100
        self.test_pubkey_coordinates = (
            107303582290733097924842193972465022053148211775194373671539518313500194639752,
            103795966108782717446806684023742168462365449272639790795591544606836007446638
        )
        self.expected_address = "0xd9A284367b6D3e25A91c91b5A430AF2593886EB9"
        self.expected_priv_pem_no_enc = """-----BEGIN EC PRIVATE KEY-----
MHQCAQEEIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABkoAcGBSuBBAAK
oUQDQgAE7Tus4jxeF2UuF0yDX7cr9T7jBrNAaiaJAiG0zvdQD4jlem9XEojM/9za
Xop6H4e/l70XvghIldD84XrV4zUobg==
-----END EC PRIVATE KEY-----
"""

        self.acc: EthAccount = EthAccount.from_secret(self.test_private)

        self.msg = "message".encode()
        self.sig_r = EthHashBytes(0x1359a4a0670e0b2d8fe43c68c724672f1d016d53cf0715b13cacc88827c284ca)
        self.sig_s = EthHashBytes(0x06e210927262217fa714f62c683106d3bd25c4e2bbd4c908f427df24824ce7b6)
        self.sig_bytes = self.sig_r + self.sig_s

    def test_init(self):
        self.assertEqual(self.acc.priv, self.test_private)
        self.assertEqual(self.acc.vk.coordinates(), self.test_pubkey_coordinates)
        self.assertEqual(self.acc.address, self.expected_address)

    def test_exporting_as_pem(self):
        # exporting private key as a PEM w/o encryption
        private_pem_without_enc: bytes = self.acc.priv_to_pem()
        self.assertEqual(private_pem_without_enc.decode(), self.expected_priv_pem_no_enc)

        # initiate object by a PEM w/o encryption
        acc_init_by_pem_no_enc = EthAccount.from_private_key_pem(private_pem_without_enc)
        self.assertEqual(acc_init_by_pem_no_enc.address, self.acc.address)

        # initiate object by a PME w/ encryption
        private_pem_with_enc: bytes = self.acc.priv_to_pem("test")
        acc_init_by_pem_with_enc = EthAccount.from_private_key_pem(private_pem_with_enc, "test")
        self.assertEqual(acc_init_by_pem_with_enc.address, self.acc.address)

        # initiate object using wrong password
        self.assertRaises(ValueError, EthAccount.from_private_key_pem, private_pem_with_enc, "test1")

    def test_ecdsa(self):
        # basic ecdsa
        sig_basic = self.acc.ecdsa_sign(self.msg)
        self.assertTrue(isinstance(sig_basic, WrappedSignature))
        self.assertTrue(EthAccount.ecdsa_verify_by_msg(self.msg, sig_basic.r, sig_basic.s, self.acc.vk))

        # recoverable_verify
        sig_recover = self.acc.ecdsa_recoverable_sign(self.msg)
        self.assertTrue(isinstance(sig_basic, WrappedSignature))

        recovered_address = EthAccount.ecdsa_recover_address(sig_recover.r, sig_recover.s, sig_recover.v, self.msg)
        self.assertEqual(recovered_address, self.acc.address)

        msg_digest = ETH_HASH(self.msg).digest()
        recovered_address = EthAccount.ecdsa_recover_address_with_digest(
            sig_recover.r, sig_recover.s, sig_recover.v, msg_digest
        )
        self.assertEqual(recovered_address, self.acc.address)
