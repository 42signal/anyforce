import pytest
from faker import Faker
from pydantic import ValidationError
from tortoise import exceptions as tortoiseExceptions

from anyforce.api import exceptions
from anyforce.model.enum import EnumMissingError

from .model import CharEnum, Model1


@pytest.mark.asyncio
async def test_exceptions(faker: Faker):
    handlers = exceptions.handlers()

    validationErrorHandle = handlers[1][1]
    try:
        Model1.detail().model_validate({})
    except ValidationError as e:
        await validationErrorHandle(None, e)

    ormException = handlers[2][1]
    await ormException(None, tortoiseExceptions.ValidationError(faker.pystr()))
    await ormException(None, tortoiseExceptions.DoesNotExist(faker.pystr()))
    await ormException(None, tortoiseExceptions.IntegrityError(faker.pystr()))
    try:
        await ormException(None, tortoiseExceptions.DBConnectionError(faker.pystr()))
    except tortoiseExceptions.DBConnectionError:
        pass

    try:
        CharEnum("c")
    except EnumMissingError as e:
        enumMissingErrorHandle = handlers[3][1]
        await enumMissingErrorHandle(None, e)
