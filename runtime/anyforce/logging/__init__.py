import logging
import os
from typing import Optional, Union

import colorama
from pythonjsonlogger import jsonlogger

from ..json import dumps
from .colorful import dumps as colorful_dumps
from .context import Context, ContextLogger
from .level import SUCCESS

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


os.environ["PYCHARM_HOSTED"] = "true"
colorama.init()
logging.addLevelName(SUCCESS, "SUCCESS")
log_level = logging.getLevelName(os.environ.get("LOGLEVEL", "INFO").upper())
logging.getLogger().setLevel(log_level)

colorful_log_handler = logging.StreamHandler()
colorful_log_handler.setFormatter(
    jsonlogger.JsonFormatter(
        "%(levelname)s %(filename) %(lineno)s %(message)s",
        json_serializer=colorful_dumps,
        json_ensure_ascii=False,
    )
)
log_handler = logging.StreamHandler()
log_handler.setFormatter(
    jsonlogger.JsonFormatter(
        "%(levelname)s %(filename) %(lineno)s %(message)s",
        json_serializer=dumps,
    )
)


def getLogger(
    name: Optional[str] = None,
    colorful: bool = True,
    level: Union[str, int] = log_level,
) -> Context:
    logger = ContextLogger(name or "", level=level)
    logger.addHandler(colorful_log_handler if colorful else log_handler)
    return logger.with_field()
