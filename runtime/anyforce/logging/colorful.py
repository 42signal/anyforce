import json
from typing import Any, Dict, List

from colorama import Fore, Style

level_colors: Dict[str, str] = {
    "CRITICAL": Fore.RED,
    "ERROR": Fore.MAGENTA,
    "WARNING": Fore.YELLOW,
    "INFO": Fore.LIGHTCYAN_EX,
    "DEBUG": Fore.LIGHTBLACK_EX,
    "SUCCESS": Fore.GREEN,
}


def dumps(record: Dict[str, Any], *args: Any, **kwargs: Any) -> str:
    level = record.pop("levelname", "UNSET")
    color = record.pop("color", level_colors.get(level, ""))
    filename = record.pop("filename", "")
    lineno = record.pop("lineno", "")
    parts: List[str] = []
    for k, v in record.items():
        if v == "" or v is None:
            continue
        parts.append(
            "%s%s: %s%s" % (color, k, Style.RESET_ALL, json.dumps(v, *args, **kwargs))
        )
    return "%s[%s]%s(%s:%s) %s" % (
        color,
        level,
        Style.RESET_ALL,
        filename,
        lineno,
        "; ".join(parts),
    )
