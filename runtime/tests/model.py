from typing import Optional

from anyforce.model import BaseUpdateModel, StrEnum, fields


class CharEnum(StrEnum):
    a = "a", "a"
    b = "b", "b"


class User(BaseUpdateModel):
    email = fields.CharField(64, index=True, null=False, description="邮箱", default="")
    hashed_password = fields.CharField(128, null=False, default="")


class Model1(BaseUpdateModel):
    name = fields.CharField(max_length=32)


class Model2(BaseUpdateModel):
    title = "测试"

    int_field = fields.IntField(title="数字字段")
    bigint_field = fields.BigIntField()
    char_enum_field = fields.CharEnumField(CharEnum)
    nullable_char_field = fields.CharField(
        max_length=32, unique=True, null=True, description="唯一字段"
    )
    default_char_field = fields.CharField(max_length=32, null=False, default="")
    required_char_field = fields.CharField(
        max_length=32, null=False, description="必填字段"
    )
    text_field = fields.TextField(default="")
    uuid_field = fields.UUIDField(null=True)
    float_field = fields.FloatField(default=0)
    date_field = fields.DateField(null=True)
    datetime_field = fields.DatetimeField(null=True)
    auto_now_field = fields.DatetimeField(null=True, auto_now=True)
    auto_now_add_field = fields.DatetimeField(null=True, auto_now_add=True)
    timedelta_field = fields.TimeDeltaField(null=True)
    json_field = fields.JSONField(default={})
    binary_field = fields.BinaryField(null=True)

    class PydanticMeta:
        arbitrary_types_allowed = True
        computed = [
            "int_field_plus_bigint_field",
            "async_int_field_plus_bigint_field",
        ]

    def int_field_plus_bigint_field(self) -> int:
        return self.int_field + self.bigint_field

    async def async_int_field_plus_bigint_field(self) -> Optional[int]:
        return self.int_field + self.bigint_field


name = __name__

__all__ = ["name"]
