import logging
import logging.handlers
import os.path

from pythonjsonlogger import jsonlogger

from ..json import fast_dumps as dumps


def get(
    path: str, maxBytes: int = 512 * 1024 * 1024, backupCount: int = 10
) -> logging.Logger:
    name = os.path.basename(path)
    logger = logging.getLogger(name)
    logHandler = logging.handlers.RotatingFileHandler(
        path, maxBytes=maxBytes, backupCount=backupCount
    )
    formatter = jsonlogger.JsonFormatter(
        json_serializer=dumps, reserved_attrs=[], timestamp="timestamp"
    )
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    return logger
