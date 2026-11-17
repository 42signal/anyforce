import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jose import jwt as jwt_lib
from pydantic import BaseModel, Field, ValidationError

from ..exceptions import HTTPUnAuthorizedError


class Claims(BaseModel):
    sub: str = Field(min_length=1)
    exp: int
    jti: str | None = None


def gen_claims(
    token_url: str,
    secret: str,
    algorithm: str = "HS256",
) -> Callable[[Request], Awaitable[Claims]]:
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl=token_url)

    async def get_current_claims(request: Request) -> Claims:
        token = await oauth2_scheme(request)
        if not token:
            raise HTTPUnAuthorizedError
        try:
            claims = Claims.model_validate(
                jwt_lib.decode(token, secret, algorithms=[algorithm])
            )
        except (JWTError, ValidationError) as error:
            raise HTTPUnAuthorizedError from error
        if claims.exp < time.time():
            raise HTTPUnAuthorizedError
        return claims

    return get_current_claims


def gen(
    token_url: str,
    secret: str,
    expire_after_seconds: int = 3600 * 24 * 30,
    algorithm: str = "HS256",
):
    get_current_claims = gen_claims(token_url, secret, algorithm)

    async def get_current_user(request: Request) -> str:
        return (await get_current_claims(request)).sub

    def authorize(
        user_id: str,
        *,
        jti: str | None = None,
        expires_at: int | None = None,
    ) -> str:
        claims = Claims(
            sub=user_id,
            exp=expires_at
            if expires_at is not None
            else int(time.time() + expire_after_seconds),
            jti=jti,
        )
        return jwt_lib.encode(
            claims.model_dump(exclude_none=True),
            secret,
            algorithm=algorithm,
        )

    return get_current_user, authorize
