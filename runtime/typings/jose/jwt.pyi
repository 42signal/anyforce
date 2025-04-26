from typing import Any

def encode(
    claims: dict[str, Any],
    key: str,
    algorithm: str | None = ...,
    headers: dict[str, str] | None = ...,
    access_token: str | None = ...,
) -> str: ...
def decode(
    token: str,
    key: str,
    algorithms: list[str] | str | None = ...,
    options: dict[str, Any] | None = ...,
    audience: str | None = ...,
    issuer: list[str] | str | None = ...,
    subject: str | None = ...,
    access_token: str | None = ...,
) -> dict[str, str]: ...
