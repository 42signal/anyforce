import json as stdjson
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi.testclient import TestClient
from requests.utils import dict_from_cookiejar  # type: ignore

from ..json import raw_dumps


class Response(object):
    def __init__(self, r: httpx.Response) -> None:
        self.r = r

    @property
    def content(self) -> bytes:
        return self.r.content

    @property
    def cookies(self) -> Dict[str, str]:
        return dict_from_cookiejar(self.r.cookies)  # type: ignore

    @property
    def text(self) -> str:
        return self.r.text

    @property
    def status_code(self) -> int:
        return self.r.status_code

    def json(self, **kwargs: Any) -> Union[Dict[str, Any], List[Any]]:
        return self.r.json(**kwargs)  # type: ignore

    def json_array(self, **kwargs: Any) -> List[Any]:
        r = self.json(**kwargs)
        assert not isinstance(r, dict)
        return r

    def json_object(self, **kwargs: Any) -> Dict[str, Any]:
        r = self.json(**kwargs)
        assert isinstance(r, dict)
        return r


def request(
    client: TestClient,
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    json: Optional[Any] = None,
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
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
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
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    json: Optional[Any] = None,
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
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    json: Optional[Any] = None,
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
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
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
