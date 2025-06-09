import logging
import os
import socket
import sys
from typing import Any

import orjson
import structlog
from structlog.types import EventDict

from .factory import gelf, multi

CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET

log_level_mapping = logging.getLevelNamesMapping()
log_level = log_level_mapping.get(
    os.environ.get("LOGLEVEL", "INFO").upper(), logging.INFO
)


def add_logger(logger: Any, method_name: str, event_dict: EventDict):
    name = getattr(logger, "name", "")
    if name:
        event_dict["logger"] = name
    return event_dict


shared_processors: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.TimeStamper(),
    add_logger,
]

gelf_address = os.environ.get("LOG_GELF_ADDRESS", "")
if gelf_address or not sys.stderr.isatty():
    hostname = socket.gethostname()

    def gelf_processor(logger: Any, method_name: str, event_dict: EventDict):
        event_dict["version"] = "1.1"
        event_dict["host"] = hostname
        event_dict["level"] = log_level_mapping.get(
            event_dict.pop("level", method_name), 1
        )
        event_dict["short_message"] = event_dict.pop("event") or "-"
        return event_dict

    processors = shared_processors + [
        structlog.processors.dict_tracebacks,
        gelf_processor,
        structlog.processors.JSONRenderer(serializer=orjson.dumps),
    ]

    enable_stdout = os.environ.get("LOG_ENABLE_STDOUT", "false") == "true"
    logger_factory = (
        multi.Factory(gelf.UDPFactory(gelf_address), structlog.BytesLoggerFactory())
        if enable_stdout
        else multi.Factory(
            gelf.UDPFactory(gelf_address)
            if gelf_address
            else structlog.BytesLoggerFactory()
        )
    )
else:
    processors = shared_processors + [structlog.dev.ConsoleRenderer()]
    logger_factory = multi.Factory(structlog.WriteLoggerFactory())

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
