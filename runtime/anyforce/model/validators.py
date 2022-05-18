from typing import Any

from email_validator import EmailNotValidError, validate_email
from tortoise.exceptions import ValidationError


def email(value: Any):
    try:
        validate_email(str(value))
    except EmailNotValidError:
        raise ValidationError(f"{value} 不是有效的邮箱地址")
