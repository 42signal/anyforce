from pypika.functions import Count
from tortoise.expressions import F
from tortoise.queryset import CountQuery


class DistinctCountQuery(CountQuery):
    def __init__(self, q: CountQuery) -> None:
        super().__init__(
            q.model,
            q._db,
            q.q_objects,
            q.annotations,
            q.custom_filters,
            q.limit,
            q.offset,
            q.force_indexes,
            q.use_indexes,
        )

    def _make_query(self) -> None:
        super()._make_query()
        meta = getattr(self.model, "_meta")
        setattr(
            self.query,
            "_selects",
            [getattr(Count(F("id", table=meta.basetable)), "distinct")()],
        )
