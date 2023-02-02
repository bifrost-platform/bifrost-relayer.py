import inspect
from chainpy.logger import global_logger


# TODO dev function
def log_invalid_flow(log_id: str, event):
    caller_func_name = inspect.stack()[1].function
    global_logger.debug(log_id, "InvalidFlow: {} called when handling {} by {}".format(
        caller_func_name,
        event.summary(),
        event.manager.active_account.address
    ))
