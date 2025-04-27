from typing import Any, AsyncContextManager, Type

from tortoise import transactions
from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    ConnectionWrapper,
    TransactionContext,
)
from tortoise.expressions import Case, CombinedExpression, Expression, F, Function, When


class Cursor:
    async def execute(
        self, sql: str, *args: tuple[Any] | list[Any] | dict[str, Any]
    ) -> None: ...
    async def fetchone(self) -> list[str | float | None] | None: ...
    async def fetchall(self) -> list[list[str | float | None]] | None: ...


class Connection:
    def cursor(
        self, cursor: Type[Cursor] | None = None
    ) -> AsyncContextManager[Cursor]: ...


class Client(BaseDBAsyncClient):
    def acquire_connection(self) -> ConnectionWrapper[Connection]: ...


def in_transaction(app: str | None = None) -> TransactionContext[Client]:
    return transactions.in_transaction(app)  # type: ignore[return-value]


def case(
    *args: When, default: str | float | F | Expression | Function | None = None
) -> CombinedExpression:
    return Case(*args, default=default)  # type: ignore
