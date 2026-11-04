import pytest
from faker import Faker
from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient

from anyforce.api.security import jwt


@pytest.mark.parametrize(
    ("token_type", "expected_status"),
    [
        ("valid", status.HTTP_200_OK),
        ("expired", status.HTTP_401_UNAUTHORIZED),
        ("invalid_signature", status.HTTP_401_UNAUTHORIZED),
        ("malformed", status.HTTP_401_UNAUTHORIZED),
    ],
)
def test_jwt(faker: Faker, token_type: str, expected_status: int):
    email = faker.email()
    secret = faker.pystr()
    get_current_user, authorize = jwt.gen(
        "/token",
        secret,
        expire_after_seconds=-60 if token_type == "expired" else 3600,
    )
    if token_type == "invalid_signature":
        _, authorize = jwt.gen("/token", f"{secret}-other")
    token = "not-a-jwt" if token_type == "malformed" else authorize(email)
    app = FastAPI()

    async def protected(user_id: str = Depends(get_current_user)):
        return {"user_id": user_id}

    app.add_api_route("/protected", protected)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == expected_status
    assert response.json() == (
        {"user_id": email}
        if expected_status == status.HTTP_200_OK
        else {"detail": {"errors": "未认证"}}
    )
