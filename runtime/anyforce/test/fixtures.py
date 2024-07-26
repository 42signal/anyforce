from typing import Iterable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tortoise import Tortoise

from ..api import exceptions


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


@pytest.fixture(scope="session")
async def database(models: Iterable[str]):
    await init_tortoise(models)
    await Tortoise.generate_schemas(False)
    yield True
    await Tortoise.close_connections()
