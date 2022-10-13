import logging.handlers

from relayer.chainpy.eth.ethtype.consts import ChainIndex
from relayer.chainpy.eth.ethtype.hexbytes import EthAddress


class LoggerSetting:
    LEVEL = logging.DEBUG
    FILENAME = "protocol.log"
    MAX_BYTES = 10 * 1024 * 1024
    BACKUP_COUNT = 10
    FORMAT = "%(asctime)s [%(name)-10s] %(message)s"


def formatted_log(
        logger_obj,
        relayer_addr: EthAddress = EthAddress.zero(),
        log_id: str = None,
        related_chain: ChainIndex = None,
        log_data: str = None):
    msg = "{}:{}:{}:{}".format(
        relayer_addr.hex()[:10],
        log_id,
        related_chain,
        log_data
    )
    logger_obj.info(msg)


def Logger(
        name: str, level=LoggerSetting.LEVEL,
        max_bytes=LoggerSetting.MAX_BYTES, _format=LoggerSetting.FORMAT, file_path=LoggerSetting.FILENAME):
    # generate logger with "name"
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # define formatter and handler
    formatter = logging.Formatter(_format)
    stream_handler = logging.StreamHandler()
    file_handler = logging.handlers.RotatingFileHandler(
        filename=file_path,
        maxBytes=max_bytes,
        backupCount=LoggerSetting.BACKUP_COUNT
    )

    # prepare handlers (both stdout and file)
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # add handlers to logger
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger
