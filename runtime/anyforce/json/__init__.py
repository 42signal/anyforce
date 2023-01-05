from datetime import datetime
from decimal import Decimal

try:
    from ciso8601 import parse_datetime  # type: ignore
except ImportError:
    from dateutil.parser import parse as parse_datetime

from typing import Any, Dict, List, Optional, Tuple, Union, cast

import orjson
from fastapi.encoders import jsonable_encoder


def fast_dumps_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError


def fast_dumps(o: Any) -> str:
    return orjson.dumps(o, default=fast_dumps_default).decode("utf-8")


def raw_dumps(o: Any) -> bytes:
    return orjson.dumps(o, default=jsonable_encoder)


def dumps(
    o: Any,
    skipkeys: bool = False,
    ensure_ascii: bool = False,
    check_circular: bool = False,
    allow_nan: bool = False,
    cls: Any = None,
    indent: Optional[int] = None,
    separators: Optional[Tuple[str, str]] = None,
    default: Any = jsonable_encoder,
    sort_keys: bool = False,
) -> str:
    option = 0
    if indent == 2:
        option |= orjson.OPT_INDENT_2
    if sort_keys:
        option |= orjson.OPT_SORT_KEYS
    return orjson.dumps(o, default=default, option=option).decode("utf-8")


def parse_iso_datetime(s: str) -> datetime:
    return parse_datetime(s)  # type: ignore


def decoder(input: Any) -> Any:
    if isinstance(input, dict):
        input = cast(Dict[Any, Any], input)
        for k, v in input.items():
            input[k] = decoder(v)
    elif isinstance(input, List):
        input = cast(List[Any], input)
        for i, v in enumerate(input):
            input[i] = decoder(v)
    elif isinstance(input, str) and input.find("T") == 10:
        try:
            return parse_iso_datetime(input)
        except ValueError:
            pass
    return input


def loads(raw: Union[bytes, bytearray, str]):
    o = orjson.loads(raw)
    return decoder(o)
