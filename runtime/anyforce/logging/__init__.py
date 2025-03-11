import logging
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

shared_processors: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.format_exc_info,
]
if sys.stderr.isatty():
    processors = shared_processors + [structlog.dev.ConsoleRenderer()]
else:
    processors = shared_processors + [
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(serializer=orjson.dumps),
    ]

structlog.configure(
    cache_logger_on_first_use=True,
    processors=processors,
    logger_factory=structlog.BytesLoggerFactory(),
)


def get_logger(*names: str, **initial_values: Any) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(*names, **initial_values)
