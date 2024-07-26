import asyncio
from datetime import datetime
from typing import Optional

from anyforce.model import BaseUpdateModel, fields


class Model(BaseUpdateModel):
    name = fields.CharField(max_length=32)

    class PydanticMeta(BaseUpdateModel.PydanticMeta):
        computed = (
            "int_field_plus_bigint_field",
            "async_int_field_plus_bigint_field",
        )

    def int_field_plus_bigint_field(self) -> int:
        return 1

    async def async_int_field_plus_bigint_field(self) -> Optional[int]:
        return 2


async def main():
    model = Model(
        id=1, name="xxxx", created_at=datetime.now(), updated_at=datetime.now()
    )
    print(model.detail().model_validate(model).model_dump(exclude_unset=True))


asyncio.run(main())
