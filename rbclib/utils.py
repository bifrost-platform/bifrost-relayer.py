import argparse
import sys


def log_invalid_flow(logger, event):
    caller_func_name = sys._getframe(1).f_code.co_name
    logger.warning("Invalid flow: {} called when handling {} by {}-th relayer".format(
        caller_func_name,
        event.summary(),
        event.manager.relayer_index
    ))


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')
