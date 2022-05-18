from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from .level import SUCCESS


class Context(object):
    def __init__(
        self,
        isEnabledFor: Callable[[int], bool],
        log: Callable[..., Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super(Context, self).__init__()
        self.isEnabledFor = isEnabledFor
        self._log = log
        self.context: Dict[str, Any] = context or {}

    def get_extras(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = self.context.copy()
        if extra:
            context.update(extra)

        # 替换特殊关键词
        for keyword in ["name", "level", "msg", "args", "exc_info", "func"]:
            val = context.pop(keyword, None)
            if val:
                context[f"{keyword}_"] = val

        return context

    def with_field(self, **kwargs: Any) -> Context:
        context = self.context.copy()
        context.update(kwargs)
        return Context(isEnabledFor=self.isEnabledFor, log=self._log, context=context)

    def debug(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(logging.DEBUG):
            return
        return self._log(
            logging.DEBUG,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )

    def info(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(logging.INFO):
            return
        return self._log(
            logging.INFO,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )

    def warning(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(logging.WARNING):
            return
        return self._log(
            logging.WARNING,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )

    def warn(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(logging.WARNING):
            return
        return self._log(
            logging.WARNING,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )

    def error(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(logging.ERROR):
            return
        return self._log(
            logging.ERROR,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )

    def exception(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(logging.ERROR):
            return
        return self._log(
            logging.ERROR,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )

    def critical(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(logging.CRITICAL):
            return
        return self._log(
            logging.CRITICAL,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )

    def success(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(SUCCESS):
            return
        return self._log(
            SUCCESS,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )

    def log(
        self,
        level: int,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not self.isEnabledFor(level):
            return
        return self._log(
            level,
            msg,
            args=args,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            *kwargs,
        )


class ContextLogger(logging.Logger):
    def with_field(self, **kwargs: Any) -> Context:
        return Context(isEnabledFor=self.isEnabledFor, log=self._log, context=kwargs)
