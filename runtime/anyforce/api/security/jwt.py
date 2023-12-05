from datetime import datetime, timedelta

from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt as jwt_lib

from ..exceptions import HTTPUnAuthorizedError


def gen(
    token_url: str,
    secret: str,
    expire_after_seconds: int = 3600 * 24 * 30,
    algorithm: str = "HS256",
):
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl=token_url)

    async def get_current_user(request: Request) -> str:
        token = await oauth2_scheme(request)
        if not token:
            raise HTTPUnAuthorizedError
        payload = jwt_lib.decode(token, secret, algorithms=[algorithm])
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPUnAuthorizedError
        exp = float(payload.get("exp", 0))
        if exp < datetime.now().timestamp():
            raise HTTPUnAuthorizedError
        return user_id

    def authorize(user_id: str) -> str:
        exp = datetime.now() + timedelta(seconds=expire_after_seconds)
        token = jwt_lib.encode(
            {"sub": user_id, "exp": int(exp.timestamp())},
            secret,
            algorithm=algorithm,
        )
        return token

    return get_current_user, authorize
