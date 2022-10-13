class EstimateGasError(Exception):
    def __init__(self, msg: str):
        super().__init__("[EstimateError]" + msg)
