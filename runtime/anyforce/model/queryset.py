from typing import Literal

from tortoise.queryset import ValuesQuery


class ValuesWithoutGroupByQuery(ValuesQuery[Literal[False]]):
    def __init__(self, q: ValuesQuery[Literal[False]]):
        super().__init__(
            db=q._db,
            model=q.model,  # type: ignore
            q_objects=q._q_objects,
            single=q._single,
            raise_does_not_exist=q._raise_does_not_exist,
            fields_for_select=q._fields_for_select,
            distinct=q._distinct,
            limit=q._limit,
            offset=q._offset,
            orderings=q._orderings,
            annotations=q._annotations,
            custom_filters=q._custom_filters,
            group_bys=q._group_bys,
            force_indexes=q._force_indexes,
            use_indexes=q._use_indexes,
        )

    def _make_query(self) -> None:
        super()._make_query()
        if not self._group_bys:
            # NOTE: resolve_filters will append joined table as groupbys
            setattr(self.query, "_groupbys", [])
