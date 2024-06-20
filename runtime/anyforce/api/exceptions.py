import re
from typing import Any, Dict, List, Match, Optional, Tuple, Union, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError, ValidationException
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
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
            loc: Tuple[str, ...] = child_e.get("loc") or ()
            path = ".".join(list(loc)[1:])

            translated_msg = validation_error_translation.get(error_type)
            if not translated_msg:
                log.warn("not translate")
                translated_msg = msg
            msgs.append(f"{path} {translated_msg}")

        else:
            msgs.append(str(child_e))
            log.warn("not translate")
    return msgs


validation_error_translation: dict[str, str] = {
    "missing": "必填写项目",
    "int_parsing": "为无效数据",
    "url_parsing": "为无效的链接",
    "string_too_long": "数据过长",
    "string_too_short": "数据过短",
}


def translate_validation_error(e: ValidationError) -> List[str]:
    msgs: List[str] = []
    for error in e.errors():
        typ: str = error["type"]
        msg: str = error["msg"]
        loc: List[str] = [str(x) for x in error["loc"]]

        log = logger.with_field(raw_error=error, raw_error_type=typ)
        translated_msg = validation_error_translation.get(typ)
        if not translated_msg:
            log.warn("not translate")
            translated_msg = msg

        path = ".".join(list(loc)[1:])
        msgs.append(f"{path} {translated_msg}")
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
            regexps = [
                ".*Duplicate entry '(.+)' for key.*",
                "UNIQUE constraint failed: .*",
            ]
            matched: Optional[Match[str]] = None
            for regexp in regexps:
                matched = re.match(regexp, str(arg))
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
    async def valueExceptionHandle(
        request: Optional[Request], exc: ValueError
    ) -> ORJSONResponse:
        msg = str(exc)
        regexps = [
            (r"invalid literal for int\(\) with base 10: '(.+)'", "{0} 不是有效的整数"),
            ("could not convert string to float: '(.+)'", "{0} 不是有效的浮点数"),
        ]
        matched: Optional[Match[str]] = None
        for regexp, msg_template in regexps:
            matched = re.match(regexp, msg)
            if matched:
                groups = matched.groups()
                msg = msg_template.format(*groups)
                break
        if not matched:
            logger.with_field(msg=msg, type=type(exc)).warn("not translate")
        return ORJSONResponse(
            {"detail": {"errors": msg}},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

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
        ([ValueError], valueExceptionHandle),
        ([RequestValidationError, ValidationError], validationErrorHandle),
        ([exceptions.BaseORMException], ormException),
        ([EnumMissingError], enumMissingErrorHandle),
        ([RequestValidationError], validationExceptionHandle),
    )


def register(app: FastAPI):
    for errors, handler in handlers():
        for e in errors:
            app.exception_handler(e)(handler)  # type: ignore
