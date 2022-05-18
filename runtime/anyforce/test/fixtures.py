import asyncio
from typing import Iterable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tortoise import Tortoise

from ..api import exceptions


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def init_tortoise(models: Iterable[str]):
    await Tortoise.init(  # type: ignore
        db_url="sqlite://:memory:", modules={"models": models}
    )


@pytest.fixture(scope="session")
async def app(models: Iterable[str]):
    await init_tortoise(models)
    app = FastAPI()
    exceptions.register(app)
    yield app


@pytest.fixture(scope="session")
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
async def database(models: Iterable[str]):
    await init_tortoise(models)
    await Tortoise.generate_schemas(False)
    yield True
    await Tortoise._drop_databases()  # type: ignore
