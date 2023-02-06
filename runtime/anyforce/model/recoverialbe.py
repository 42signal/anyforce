from datetime import datetime
from typing import Any, Dict, Optional

from tortoise import fields
from tortoise.backends.base.client import BaseDBAsyncClient

from .base import BaseUpdateModel


class RecoverableModel(BaseUpdateModel):
    is_deleted = fields.BooleanField(null=False, description="是否已经删除", default=False)
    delete_or_recover_at = fields.DatetimeField(null=True, description="删除时间")

    class meta:
        abstract = True

    async def update(self, input: Any):
        dic: Dict[str, Any] = (
            input if isinstance(input, dict) else input.dict(exclude_unset=True)
        )
        is_deleted = dic.get("is_deleted")
        if is_deleted is not None and self.is_deleted != is_deleted:
            dic["delete_or_recover_at"] = datetime.now()
        return await super().update(dic)

    async def delete(self, using_db: Optional[BaseDBAsyncClient] = None) -> None:
        await self.update(
            {
                "is_deleted": True,
                "delete_or_recover_at": datetime.now(),
            }
        )
        await self.save()
        return
