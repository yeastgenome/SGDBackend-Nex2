import os
import logging
import logging.handlers
from pathlib import Path


DEFAULT_FORMATTER = logging.Formatter(logging.BASIC_FORMAT)
DEFAULT_LEVEL = "INFO"
DEFAULT_LOGFILE = os.environ.get("LOG_FILE")
ENV = os.environ.get("ENV", "prod")


def setup_logger(log_name, log_file_path=DEFAULT_LOGFILE,
                 custom_formatter=None, level=DEFAULT_LEVEL, is_file=True):
    """ Setup loggers
    
    Parameters
    ----------
    name: string
    custom_formatter: string
    log_file_path: string
    level: obj(translated as integer)
        Default is INFO object. Other options include
        CRITICAL, ERROR, WARNING, DEBUG, NOTSET
    is_file: bool
        File handler is default
    
    Returns
    -------
    logger: obj

    Notes
    -----
    Handler object is never instantiated directly. Useful for custom loggers
    Logger only logs with severity level of Warning or above
    basicConfig() can only be called once

    """

    try:
        # set handlers
        handler = None

        if(is_file):
            if ENV == "dev" or ENV == "test":
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            handler = logging.FileHandler(log_file_path)
        else:
            handler = logging.StreamHandler()
        if custom_formatter:
            formatter = logging.Formatter(custom_formatter)
            handler.setFormatter(formatter)
        else:
            handler.setFormatter(DEFAULT_FORMATTER)

        # set logger
        logger = logging.getLogger(log_name)
        logger.setLevel(level)
        logger.addHandler(handler)

        return logger

    except Exception as e:
        print("log file not found", e)
