import json

import eth_abi
from dataclasses_json import dataclass_json, LetterCase
from dataclasses import dataclass
from typing import Optional, List, Dict

from .hexbytes import EthHashBytes, EthHexBytes, EthAddress
from .utils import *
from .exceptions import *


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MethodInput:
    internal_type: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    indexed: Optional[bool] = None
    components: Optional[List["MethodInput"]] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MethodOutput:
    internal_type: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    indexed: Optional[bool] = None
    components: Optional[List["MethodOutput"]] = None


def get_type_strings(components_list: List, substitutions: Optional[Dict] = None) -> List:
    """Converts a list of parameters from an ABI into a list of type strings."""
    types_list = []
    if substitutions is None:
        substitutions = {}

    for method_input in components_list:
        if method_input.type.startswith("tuple"):
            params = get_type_strings(method_input.components, substitutions)
            array_size = method_input.type[5:]
            types_list.append(f"({','.join(params)}){array_size}")
        else:
            type_str = method_input.type
            for orig, sub in substitutions.items():
                if type_str.startswith(orig):
                    type_str = type_str.replace(orig, sub)
            types_list.append(type_str)
    return types_list


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AbiMethod:
    type: str
    inputs: List[MethodInput]
    state_mutability: str = Optional[str]
    name: Optional[str] = None
    outputs: Optional[List[MethodOutput]] = None
    anonymous: Optional[bool] = None

    def __post_init__(self):
        self.inputs = [MethodInput.from_dict(inp) for inp in self.inputs]
        if self.outputs is not None:
            self.outputs = [MethodOutput.from_dict(oup) for oup in self.outputs]

    @staticmethod
    def from_abi_list(method_name: str, abi_list: list) -> Union["AbiMethod", None]:
        for abi_method_dict in abi_list:
            if abi_method_dict["name"] == method_name:
                return AbiMethod.from_dict(abi_method_dict)
        return None

    def get_input_types_list(self) -> list:
        return get_type_strings(self.inputs)

    def get_output_types_list(self) -> list:
        return get_type_strings(self.outputs)

    def get_signature(self) -> str:
        self.name = "constructor" if self.name is None else self.name
        input_list = self.get_input_types_list()
        return self.name + "(" + ",".join(input_list) + ")"

    def get_selector(self) -> EthHexBytes:
        topic_bytes = EthHashBytes(self.get_topic()).bytes()
        return EthHexBytes(topic_bytes[:4])

    def get_topic(self) -> EthHashBytes:
        pre_image = self.get_signature()
        topic_bytes = ETH_HASH(pre_image.encode()).digest()
        return EthHashBytes(topic_bytes)

    def decode_input_data(self, encoded_data: EthHexBytes):
        # TODO test, where is function selector??
        types_list = self.get_input_types_list()
        return eth_abi.decode_abi(types_list, encoded_data)

    def decode_output_data(self, encoded_data: Union[str, EthHexBytes]):
        if isinstance(encoded_data, str):
            encoded_data = EthHexBytes(encoded_data)
        types_list = self.get_output_types_list()
        return eth_abi.decode_abi(types_list, encoded_data)

    def encode_input_data(self, params: Union[list, tuple]) -> EthHexBytes:
        types_list = self.get_input_types_list()
        input_data = eth_abi.encode_abi(types_list, params)
        selector = self.get_selector()
        return selector + input_data

    def encode_input_data_without_selector(self, params: Union[list, tuple]) -> EthHexBytes:
        encoded_params = self.encode_input_data(params)
        return encoded_params[4:]

    def encode_output_data(self, params: Union[list, tuple]) -> EthHexBytes:
        types_list = self.get_input_types_list()
        out_data = eth_abi.encode_abi(types_list, params)
        return EthHexBytes(out_data)


class Abi:
    def __init__(self, method_list: List[dict]):
        self.method_map = dict()

        for method in method_list:
            if "name" not in method:
                # ignore constructor and fallback method
                continue
            if method["name"] not in self.method_map:
                self.method_map[method["name"]] = method
            elif method["name"] in self.method_map:
                print("error: {}".format(method["name"]))
                raise EthAlreadyExistError(key=method["name"])
            else:
                raise EthUnknownSpecError("function in abi has no name")
        self.__cache = dict()

    @classmethod
    def from_json_file(cls, path: str):
        with open(path, "r") as json_data:
            method_list = json.load(json_data)
        return cls(method_list)

    def get_method(self, name: str) -> AbiMethod:
        if name not in self.__cache:
            method = self.method_map[name]
            method_obj = AbiMethod.from_dict(method)
            self.__cache[name] = method_obj
        return self.__cache[name]


class EthContract:
    def __init__(self, contract_name: str, contract_address: EthAddress, abi_obj: Abi):
        self.__contract_name = contract_name
        self.__contract_address = contract_address
        self.__abi = abi_obj
        self.__user_account = None

    @classmethod
    def from_abi_file(cls, contract_name: str, contract_address: EthAddress, abi_file_path: str):
        abi_obj = Abi.from_json_file(abi_file_path)
        return cls(contract_name, contract_address, abi_obj)

    @property
    def contract_name(self) -> str:
        return self.__contract_name

    @property
    def address(self) -> EthAddress:
        return self.__contract_address

    @property
    def abi(self) -> Abi:
        return self.__abi

    def get_method_abi(self, method_name: str) -> AbiMethod:
        return self.__abi.get_method(method_name)

    def decode_event(self, event_name: str, data: EthHexBytes) -> tuple:
        abi = self.get_method_abi(event_name)
        return abi.decode_input_data(data)
