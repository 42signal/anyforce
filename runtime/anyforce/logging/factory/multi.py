import pickle
from typing import Any, Callable

from structlog.typing import WrappedLogger


class Multi:
    def __init__(self, loggers: list[WrappedLogger], name: str = "") -> None:
        self.loggers = loggers
        self.name = name

    def __getstate__(self):
        return pickle.dumps(self.loggers)

    def __setstate__(self, state: Any) -> None:
        self.loggers = pickle.loads(state)

    def __deepcopy__(self, memodict: dict[str, object]):
        new_self = self.__class__(self.loggers)
        return new_self

    def __repr__(self) -> str:
        return f"<Multi(loggers={[repr(logger) for logger in self.loggers]})>"

    def msg(self, message: bytes):
        for logger in self.loggers:
            logger.msg(message)

    log = debug = info = warn = warning = msg
    fatal = failure = err = error = critical = exception = msg


class Factory:
    def __init__(self, *factories: Callable[..., WrappedLogger]):
        self.factories = factories

    def __call__(self, *args: Any):
        return Multi([factory() for factory in self.factories], args[0] if args else "")
