import logging
import os
import sys
from typing import Any

import orjson
import structlog

CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET

log_level = logging.getLevelNamesMapping().get(
    os.environ.get("LOGLEVEL", "INFO").upper(), logging.INFO
)

shared_processors: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]
if sys.stderr.isatty():
    processors = shared_processors + [structlog.dev.ConsoleRenderer()]
    logger_factory = structlog.WriteLoggerFactory()
else:
    processors = shared_processors + [
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(serializer=orjson.dumps),
    ]
    logger_factory = structlog.BytesLoggerFactory()

structlog.configure(
    cache_logger_on_first_use=True,
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    processors=processors,
    logger_factory=logger_factory,
)


def get_logger(
    *names: str, **initial_values: Any
) -> structlog.typing.FilteringBoundLogger:
    return structlog.get_logger(*names, **initial_values)
