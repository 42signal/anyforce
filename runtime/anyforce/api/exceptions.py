import re
from typing import Any, Dict, List, Match, Optional, Tuple, Union, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError, ValidationException
from fastapi.responses import ORJSONResponse
from pydantic import (
    AnyStrMaxLengthError,
    EmailError,
    IntegerError,
    ListError,
    MissingError,
    UrlError,
    ValidationError,
)
from pydantic.error_wrappers import ErrorWrapper
from tortoise import exceptions

from ..logging import getLogger
from ..model.enum import EnumMissingError

logger = getLogger(__name__)

HTTPForbiddenError = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN, detail={"errors": "禁止访问"}
)
HTTPNotFoundError = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail={"errors": "不存在"}
)
HTTPUnAuthorizedError = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail={"errors": "未认证"}
)
HTTPPreconditionRequiredError = HTTPException(
    status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail={"errors": "请求数据已过期"}
)


ValidateError = Union[RequestValidationError, ErrorWrapper, ValidationError]


def translate_validation_exception(e: ValidationException) -> List[str]:
    msgs: List[str] = []
    for child_e in e.errors():
        log = logger.with_field(e=child_e, raw_error_type=type(child_e))
        if isinstance(child_e, ValidationError):
            msgs += translate_validation_error(child_e)
        elif isinstance(child_e, dict):
            child_e = cast(Dict[str, Any], child_e)
            msg = child_e.get("msg", str(child_e))
            error_type: str = child_e.get("type", "")
            loc: Tuple[str, ...] = child_e.get("loc", ())[1:]
            path = ".".join(list(loc))
            if error_type == "value_error.missing":
                msgs.append(f"{path} 是必填项")
            elif error_type == "value_error.any_str.max_length":
                msgs.append(f"{path} 过长")
            elif error_type == "type_error.list":
                msgs.append(f"{path} 不是有效的数组")
            elif error_type == "type_error.integer":
                msgs.append(f"{path} 不是有效的整数")
            elif error_type == "value_error.email":
                msgs.append(f"{path} 不是有效的 Email")
            elif error_type == "json_invalid":
                msgs.append(f"{path} 不是有效 JSON")
            elif error_type.startswith("value_error.url"):
                msgs.append(f"{path} 不是有效的链接")
            else:
                msgs.append(msg)
                log.warn("not translate")
        else:
            msgs.append(str(child_e))
            log.warn("not translate")
    return msgs


def translate_validation_error(e: ValidationError) -> List[str]:
    msgs: List[str] = []
    model: Any = e.model
    raw_errors = e.raw_errors
    for raw_error in raw_errors:
        log = logger.with_field(raw_error=raw_error, raw_error_type=type(raw_error))
        if isinstance(raw_error, ErrorWrapper):
            inner_exc = getattr(raw_error, "exc")

            if isinstance(inner_exc, ValidationError):
                msgs += translate_validation_error(inner_exc)
                continue

            translated_msg = ""
            if isinstance(inner_exc, MissingError):
                translated_msg = "是必填项"
            elif isinstance(inner_exc, IntegerError):
                translated_msg = "为无效的整数"
            elif isinstance(inner_exc, EmailError):
                translated_msg = "为无效的邮箱地址"
            elif isinstance(inner_exc, UrlError):
                translated_msg = "为无效的链接"
            elif isinstance(inner_exc, AnyStrMaxLengthError):
                translated_msg = "数据过长"
            elif isinstance(inner_exc, ListError):
                continue
            else:
                # TODO: translate more if needed
                log.with_field(
                    inner_exc=inner_exc, inner_exc_type=type(inner_exc)
                ).warn("not translate")

            if translated_msg:
                for loc in raw_error.loc_tuple():
                    property = model.schema().get("properties", {}).get(loc, {})
                    title: str = (
                        property.get("description") or property.get("title") or str(loc)
                    )
                    msgs.append(f"{title} {translated_msg}")
                continue
        else:
            log.warn("not translate")
        msgs.append(str(raw_error))
    return msgs


def translate_validate_error(
    e: Union[ValidationError, List[ValidationError]]
) -> List[str]:
    msgs: List[str] = []
    errors: List[Any] = e if isinstance(e, List) else [e]
    for error in errors:
        msgs += translate_validation_error(error)
    return msgs


def translate_orm_error(
    e: exceptions.BaseORMException,
) -> Tuple[int, List[str]]:
    if isinstance(e, exceptions.IntegrityError):
        status_code = status.HTTP_400_BAD_REQUEST
        args: List[str] = []
        for arg in e.args:
            regxps = [
                ".*Duplicate entry '(.+)' for key.*",
                "UNIQUE constraint failed: .*",
            ]
            matched: Optional[Match[str]] = None
            for regxp in regxps:
                matched = re.match(regxp, str(arg))
                if matched:
                    status_code = status.HTTP_409_CONFLICT
                    groups = matched.groups()
                    value = groups and groups[0] or ""
                    arg = f"值为 {value} 的对象已存在" if value else "对象已存在"
                    break
            if not matched:
                logger.with_field(arg=arg, type=type(arg)).warn("not translate")
            args.append(str(arg))
        return status_code, args
    if isinstance(e, exceptions.ValidationError):
        return status.HTTP_400_BAD_REQUEST, [str(args) for args in e.args]
    if isinstance(e, exceptions.DoesNotExist):
        return status.HTTP_404_NOT_FOUND, ["不存在"]
    raise e


def handlers():
    async def validationExceptionHandle(
        request: Optional[Request], exc: ValidationException
    ) -> ORJSONResponse:
        return ORJSONResponse(
            {"detail": {"errors": translate_validation_exception(exc)}},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    async def validationErrorHandle(
        request: Optional[Request], exc: ValidationError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            {"detail": {"errors": translate_validate_error(exc)}},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    async def ormException(
        request: Optional[Request], exc: exceptions.BaseORMException
    ) -> ORJSONResponse:
        status_code, msgs = translate_orm_error(exc)
        return ORJSONResponse(
            {"detail": {"errors": msgs}},
            status_code=status_code,
        )

    async def enumMissingErrorHandle(
        request: Optional[Request], exc: EnumMissingError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            {"detail": {"errors": [str(args) for args in exc.args]}},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return (
        ([RequestValidationError, ValidationError], validationErrorHandle),
        ([exceptions.BaseORMException], ormException),
        ([EnumMissingError], enumMissingErrorHandle),
        ([RequestValidationError], validationExceptionHandle),
    )


def register(app: FastAPI):
    for errors, handler in handlers():
        for e in errors:
            app.exception_handler(e)(handler)  # type: ignore
