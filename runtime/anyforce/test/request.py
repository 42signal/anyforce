import json as stdjson
from typing import Any

import httpx
from fastapi.testclient import TestClient

from ..json import raw_dumps


class Response(object):
    def __init__(self, r: httpx.Response) -> None:
        self.r = r

    @property
    def content(self) -> bytes:
        return self.r.content

    @property
    def text(self) -> str:
        return self.r.text

    @property
    def status_code(self) -> int:
        return self.r.status_code

    def json(self, **kwargs: Any) -> dict[str, Any] | list[Any]:
        return self.r.json(**kwargs)

    def json_array(self, **kwargs: Any) -> list[Any]:
        r = self.json(**kwargs)
        assert not isinstance(r, dict)
        return r

    def json_object(self, **kwargs: Any) -> dict[str, Any]:
        r = self.json(**kwargs)
        assert isinstance(r, dict)
        return r


def request(
    client: TestClient,
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    json: Any | None = None,
    follow_redirects: bool = True,
    *args: Any,
    **kwargs: Any,
) -> Response:
    if json:
        json = stdjson.loads(raw_dumps(json))
    r = client.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json,
        follow_redirects=follow_redirects,
        *args,
        **kwargs,
    )
    return Response(r)


def get(
    client: TestClient,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    *args: Any,
    **kwargs: Any,
) -> Response:
    return request(
        client,
        "GET",
        url,
        params=params,
        headers=headers,
        *args,
        **kwargs,
    )


def post(
    client: TestClient,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    json: Any | None = None,
    *args: Any,
    **kwargs: Any,
) -> Response:
    return request(
        client,
        "POST",
        url,
        params=params,
        headers=headers,
        json=json,
        *args,
        **kwargs,
    )


def put(
    client: TestClient,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    json: Any | None = None,
    *args: Any,
    **kwargs: Any,
) -> Response:
    return request(
        client,
        "PUT",
        url,
        params=params,
        headers=headers,
        json=json,
        *args,
        **kwargs,
    )


def delete(
    client: TestClient,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    *args: Any,
    **kwargs: Any,
) -> Response:
    return request(
        client,
        "DELETE",
        url,
        params=params,
        headers=headers,
        *args,
        **kwargs,
    )
