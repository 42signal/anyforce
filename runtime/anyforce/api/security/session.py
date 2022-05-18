from fastapi import Request

from ..exceptions import HTTPUnAuthorizedError


def gen():
    async def get_current_user(request: Request) -> str:
        user_id: str = request.session.get("user_id")  # type: ignore
        if not user_id:
            raise HTTPUnAuthorizedError
        return user_id

    def authorize(request: Request, user_id: str):
        request.session["user_id"] = user_id  # type: ignore

    return get_current_user, authorize
