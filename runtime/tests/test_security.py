import time

from faker import Faker
from fastapi import Request
from jose import ExpiredSignatureError

from anyforce.api.security import jwt, password_context

from .model import User


async def test_jwt(database: bool, faker: Faker):
    assert database
    email = faker.email()
    password = faker.pystr()
    await User.create(
        email=email,
        hashed_password=password_context.hash(password),
    )
    get_current_user, authorize = jwt.gen("", faker.name(), expire_after_seconds=1)
    token = authorize(email)

    request = Request(
        {
            "type": "http",
            "headers": [("authorization".encode(), (f"Bearer {token}").encode())],
        }
    )
    authed_user = await get_current_user(request)
    assert authed_user == email

    time.sleep(2)
    try:
        await get_current_user(request)
        assert False
    except ExpiredSignatureError:
        pass
