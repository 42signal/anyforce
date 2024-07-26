import asyncio

import pytest
from faker import Faker
from fastapi import Request
from jose import ExpiredSignatureError

from anyforce.api.security import jwt

from .model import User


@pytest.mark.asyncio
async def test_jwt(database: bool, faker: Faker):
    assert database
    email = faker.email()
    await User.create(
        email=email,
        hashed_password=faker.pystr(),
    )
    get_current_user, authorize = jwt.gen("", faker.name(), expire_after_seconds=1)
    token = authorize(email)

    request = Request(
        {
            "type": "http",
            "headers": [("authorization".encode(), (f"Bearer {token}").encode())],
        }
    )
    auth_user = await get_current_user(request)
    assert auth_user == email

    await asyncio.sleep(2)
    try:
        await get_current_user(request)
        assert False
    except ExpiredSignatureError:
        pass
