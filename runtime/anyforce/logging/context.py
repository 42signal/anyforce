from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .level import SUCCESS


class Context(object):
    def __init__(
        self,
        logger: logging.Logger,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super(Context, self).__init__()
        self.logger = logger
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
        return Context(logger=self.logger, context=context)

    def debug(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
        stack_info: bool = False,
        **kwargs: Any,
    ):
        self.logger.debug(
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
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
    ):
        self.logger.info(
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
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
    ):
        self.logger.warning(
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
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
    ):
        self.logger.warn(
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
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
    ):
        self.logger.error(
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
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
    ):
        self.logger.exception(
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
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
    ):
        self.logger.critical(
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
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
    ):
        self.logger.log(
            SUCCESS,
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
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
    ):
        self.logger.log(
            level,
            msg,
            exc_info=exc_info,
            extra=self.get_extras(extra),
            stack_info=stack_info,
            stacklevel=2,
            *args,
            *kwargs,
        )


class ContextLogger(logging.Logger):
    def with_field(self, **kwargs: Any) -> Context:
        return Context(logger=self, context=kwargs)
