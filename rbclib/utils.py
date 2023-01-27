import sys


# TODO dev function
def log_invalid_flow(logger, event):
    caller_func_name = sys._getframe(1).f_code.co_name
    logger.debug("Invalid flow: {} called when handling {} by {}".format(
        caller_func_name,
        event.summary(),
        event.manager.active_account.address
    ))
