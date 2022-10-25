class EstimateGasError(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class RpcExceededTimeout(Exception):
    def __init__(self, msg: str):
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))


class RpcEVMError(Exception):
    def __init__(self, msg: str):
        msg = msg.replace("VM Exception while processing transaction: ", "")
        super().__init__("[{}] {}".format(self.__class__.__name__, msg))
