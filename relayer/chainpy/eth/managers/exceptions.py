class EstimateGasError(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class RpcExceededTimeout(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class RpcAlreadyImported(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class RpcEVMError(Exception):
    def __init__(self, msg: str):
        parsed_msg = msg.replace("VM Exception while processing transaction: ", "")
        parsed_msg = parsed_msg.replace("execution reverted: ", "")

        super().__init__("[{}] {}".format(self.__class__.__name__, parsed_msg))
