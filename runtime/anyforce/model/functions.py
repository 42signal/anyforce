from typing import Any

from pypika_tortoise.terms import ArithmeticExpression, Case, Criterion
from tortoise import transactions
from tortoise.backends.base.client import TransactionContext


def in_transaction(app: str | None = None) -> TransactionContext[Any]:
    return transactions.in_transaction(app)  # type: ignore


def case(when: Criterion, then: Any, else_: Any) -> ArithmeticExpression:
    return Case().when(when, then).else_(else_)  # type: ignore
