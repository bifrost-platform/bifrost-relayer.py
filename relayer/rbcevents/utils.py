import sys


# TODO just for dev function
def log_invalid_flow(logger, event):
    caller_func_name = sys._getframe(1).f_code.co_name
    logger.warning("Invalid flow: {} called when handling {} by {}-th relayer".format(
        caller_func_name,
        event.summary(),
        event.manager.relayer_index
    ))
