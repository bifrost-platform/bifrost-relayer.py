from typing import TYPE_CHECKING, Union

from ..chainpy.eventbridge.chaineventabc import ChainEventABC
from ..chainpy.eth.ethtype.account import EthAccount
from ..chainpy.eth.ethtype.hexbytes import EthHashBytes, EthHexBytes
from ..chainpy.eth.ethtype.utils import recursive_tuple_to_list

if TYPE_CHECKING:
    from .chainevents import RbcEvent, ValidatorSetUpdatedEvent


SigType = Union[list, tuple]


class SocketSignature:
    """
    Signature Data class from Socket contract.
     - ecdsa signature: r(32-bytes), s(32-bytes), v(1-bytes)
    Target object has the following members
     - r_list: list of r
     - s_list: list of s
     - v_list: concatenated bytes of v
    """

    def __init__(self, decoded_sigs: SigType):
        decoded_sig_list = recursive_tuple_to_list(decoded_sigs)
        if len(decoded_sig_list) != 3:
            raise Exception("signature type error")
        self.__sigs = recursive_tuple_to_list(decoded_sigs)

        sig_num = len(decoded_sigs[0])
        if sig_num != len(decoded_sigs[1]) or sig_num != len(decoded_sigs[2]):
            raise Exception("Not matched list size")
        self.__sig_num = sig_num

    @classmethod
    def init(cls):
        empty_sigs = ([], [], b'')
        return cls(empty_sigs)

    @classmethod
    def from_single_sig(cls, r: int, s: int, v: int):
        new_sig = ([EthHashBytes(r)], [EthHashBytes(s)], EthHexBytes(v))
        return cls(new_sig)

    @property
    def size(self) -> int:
        return self.__sig_num

    def tuple(self):
        return self.__sigs

    def merge_sigs(self, other: "SocketSignature"):
        if not isinstance(other, SocketSignature):
            raise Exception("other type must \"SocketSignature\", but {}".format(type(other)))
        other_sigs = other.tuple()
        self.__sigs[0] += other_sigs[0]  # append list of r
        self.__sigs[1] += other_sigs[1]  # append list of s
        self.__sigs[2] += other_sigs[2]  # append list of v
        self.__sig_num += other.size

    def get_single_sig(self, _index: int) -> (EthHexBytes, EthHexBytes, EthHashBytes):
        if self.__sig_num <= _index:
            raise Exception("Out of bound signature")

        r_list, s_list, v_bytes = self.__sigs[0], self.__sigs[1], self.__sigs[2]
        return EthHexBytes(r_list[_index]), EthHexBytes(s_list[_index]), EthHexBytes(v_bytes[_index])


class SubmitWithSig:
    def __init__(self, event: "ChainEventABC"):
        self.event = event
        self.sigs = SocketSignature.init()
        self.__decoded_data_tuple_cache = None

    @property
    def decoded_data_tuple(self):
        if self.__decoded_data_tuple_cache is None:
            self.__decoded_data_tuple_cache = self.event.manager.decode_event(self.event.detected_event)
        return self.__decoded_data_tuple_cache

    def add_single_sig(self, r: int, s: int, v: int):
        sigs = SocketSignature(([EthHashBytes(r)], [EthHashBytes(s)], EthHexBytes(v)))
        self.sigs.merge_sigs(sigs)
        return self

    def add_sigs(self, sigs: SocketSignature):
        self.sigs.merge_sigs(sigs)
        return self

    def add_tuple_sigs(self, data: tuple):
        socket_sigs = SocketSignature(data)
        self.sigs.merge_sigs(socket_sigs)
        return self

    def _sort_sigs(self):
        if self.sigs.size == 1:
            return None

        msg = self.event.detected_event.data
        sig_dict = dict()

        clone_sigs = self.sigs
        self.sigs = SocketSignature.init()
        for i in range(clone_sigs.size):
            r, s, v = clone_sigs.get_single_sig(i)
            addr = EthAccount.ecdsa_recover_address(r.int(), s.int(), v.int(), msg)
            sig_dict[addr.hex()] = (r, s, v)

        sorted_sigs = sorted(sig_dict.items())
        for sig in sorted_sigs:
            r, s, v = sig[1]
            self.add_single_sig(r.int(), s.int(), v.int())


class PollSubmit(SubmitWithSig):
    TEST_MODE = False
    """
    Data conversion class from "ChainEvent" to transaction parameters for "poll method"
    """
    def __init__(self, event: "RbcEvent"):
        super(PollSubmit, self).__init__(event)

    def submit_tuple(self, fail_option: bool = False) -> list:
        # decode event
        decoded_socket_msg = self.event.manager.decode_event(self.event.detected_event)
        decoded_socket_msg_contents = recursive_tuple_to_list(decoded_socket_msg[0])

        # convert flag from bool to int
        forced_fail = 1 if fail_option else 0

        # prepare sig to return
        # status = decoded_socket_msg_contents[1]
        self._sort_sigs()

        # return params
        params = [decoded_socket_msg_contents, self.sigs.tuple(), forced_fail]
        return [params]


class AggregatedRoundUpSubmit(SubmitWithSig):
    def __init__(self, event: "ValidatorSetUpdatedEvent"):
        super(AggregatedRoundUpSubmit, self).__init__(event)

    @property
    def status(self) -> int:
        return self.decoded_data_tuple[0]

    @property
    def round(self) -> int:
        return self.decoded_data_tuple[1][0]

    @property
    def validator_list(self) -> list:
        validator_list = self.decoded_data_tuple[1][1]
        return sorted(validator_list)

    def submit_tuple(self) -> list:
        if self.sigs is None:
            raise Exception("Not initiated sig")

        submit_param = [self.round, self.validator_list, self.sigs.tuple()]
        return [submit_param]
