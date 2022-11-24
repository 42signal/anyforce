from typing import Any, Optional

from pypika.functions import DistinctOptionFunction
from pypika.queries import QueryBuilder
from pypika.terms import Field as pikaField
from pypika.terms import Order


class GroupConcat(DistinctOptionFunction):
    def __init__(
        self,
        term: pikaField,
        order: Order = Order.asc,
        sep: str = ",",
        distinct: bool = True,
        alias: Optional[str] = None,
    ):
        super().__init__("GROUP_CONCAT", term, alias=alias)  # type: ignore
        self.term_ = term.get_sql(with_alias=False, quote_char=QueryBuilder.QUOTE_CHAR)
        self.order = order
        self.sep = self.wrap_constant(sep)  # type: ignore
        setattr(self, "_distinct", distinct)

    def get_special_params_sql(self, **kwargs: Any):
        return f"ORDER BY {self.term_} {self.order.value} SEPARATOR {self.sep}"
