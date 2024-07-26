import re
from typing import Any, Dict, List, Match, Optional, Set, Tuple, Union, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError, ValidationException
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
from pydantic_core import ErrorDetails
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
    status_code=status.HTTP_428_PRECONDITION_REQUIRED,
    detail={"errors": "请求数据已过期"},
)


validation_error_translation: dict[str, str] = {
    "bool_parsing": "无法解析为布尔值",
    "bool_type": "不是有效的布尔值",
    "date_from_datetime_inexact": "不完整的日期",
    "date_from_datetime_parsing": "无法从日期时间解析出日期",
    "date_future": "不是将来的日期",
    "date_parsing": "无法解析日期",
    "date_past": "不是过去的日期",
    "date_type": "不是有效的日期",
    "datetime_from_date_parsing": "无法从日期解析出日期时间",
    "datetime_future": "不是将来的日期时间",
    "datetime_object_invalid": "不是有效的日期时间对象",
    "datetime_parsing": "无法解析为日期时间",
    "datetime_past": "不是过去的日期时间",
    "datetime_type": "不是有效的日期时间",
    "decimal_max_digits": "定点数数字过多",
    "decimal_max_places": "定点数小数部分过多",
    "decimal_parsing": "无法解析为定点数",
    "decimal_type": "不是有效的定点数",
    "decimal_whole_digits": "定点数整数部分过多",
    "dict_type": "不是有效的字典",
    "enum": "枚举不存在",
    "finite_number": "无穷大",
    "float_parsing": "无法解析为浮点数",
    "float_type": "不是有效的浮点数",
    "get_attribute_error": "无法获取属性",
    "greater_than": "过大",
    "greater_than_equal": "过大或等于",
    "int_from_float": "无法从浮点数解析为整数",
    "int_parsing": "无法解析为整数",
    "int_type": "不是有效的整数",
    "invalid_key": "不是有效的键值",
    "is_instance_of": "不是有效的类型",
    "is_subclass_of": "不是有效的父类型",
    "iterable_type": "不可迭代",
    "iteration_error": "不是有效的迭代器",
    "json_invalid": "无法解析为 JSON",
    "json_type": "不是有效的 JSON",
    "less_than": "过小",
    "less_than_equal": "过小或等于",
    "list_type": "不是有效的数组",
    "literal_error": "不是有效的字符",
    "mapping_type": "不是有效的映射",
    "missing": "为必填项目",
    "model_attributes_type": "无法获取模型属性",
    "model_type": "不是有效的模型",
    "multiple_of": "不是有效的倍数",
    "no_such_attribute": "不存在该属性",
    "none_required": "只允许 null",
    "recursion_loop": "死循环",
    "set_type": "不是有效的集合",
    "string_pattern_mismatch": "不符合字符串规则",
    "string_sub_type": "不是有效的字符类型",
    "string_too_long": "字符串过长",
    "string_too_short": "字符串过短",
    "string_type": "不是有效的字符",
    "string_unicode": "不是有效的字符编码",
    "time_delta_parsing": "无法解析为时间间隔",
    "time_delta_type": "不是有效的时间间隔",
    "time_parsing": "无法解析为时间",
    "time_type": "不是有效的时间",
    "timezone_aware": "缺少时区",
    "timezone_naive": "不是本地时间",
    "too_long": "太长",
    "too_short": "太短",
    "tuple_type": "不是有效的元祖",
    "url_parsing": "无法解析为链接",
    "url_scheme": "不是有效的链接协议",
    "url_syntax_violation": "不符合有效的链接规则",
    "url_too_long": "链接太长",
    "url_type": "不是有效的链接",
    "uuid_parsing": "无法解析为 UUID",
    "uuid_type": "不是有效的 UUID",
    "uuid_version": "不是有效的 UUID 版本",
    "value_error": "不是有效的值",
}


def translate_validation_exception(e: ValidationException):
    msgs: Set[str] = set()
    for child_e in e.errors():
        if isinstance(child_e, ValidationError):
            msgs = msgs.union(translate_validation_error(child_e))
        elif isinstance(child_e, dict):
            msgs.add(translate_validation_error_detail(cast(Dict[str, Any], child_e)))
        else:
            msgs.add(str(child_e))
            logger.with_field(e=child_e, raw_error_type=type(child_e)).warn(
                "not translate"
            )
    return list(msgs)


def translate_validation_error(e: ValidationError):
    msgs: Set[str] = set()
    for error in e.errors():
        msgs.add(translate_validation_error_detail(error))
    return msgs


def translate_validation_error_detail(e: dict[str, Any] | ErrorDetails):
    typ: str = e.get("type", "")
    msg: str = e.get("msg", "")
    value = e["input"] or ""
    path = ".".join([str(x) for x in e.get("loc", [])])

    translate_msg = validation_error_translation.get(typ)
    if not translate_msg:
        logger.with_field(raw_error=e, raw_error_type=type(e), msg=msg).info(
            "translate exception"
        )
    msg = translate_msg or msg

    return f"{value} {msg}: {path}"


def translate_validate_error(e: Union[ValidationError, List[ValidationError]]):
    msgs: Set[str] = set()
    errors: List[Any] = e if isinstance(e, List) else [e]
    for error in errors:
        msgs = msgs.union(translate_validation_error(error))
    return list(msgs)


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
            app.exception_handler(e)(handler)
