from typing import Any, Dict, List, Optional, Union

import requests
from requests.utils import dict_from_cookiejar

from ..json import raw_dumps


class Response(object):
    def __init__(self, r: requests.Response) -> None:
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
    def raw(self) -> Any:
        return self.r.raw

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
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    json: Optional[Any] = None,
    session: Optional[requests.Session] = None,
    allow_redirects: bool = True,
    *args: Any,
    **kwargs: Any,
) -> Response:
    request_session = session or requests.session()
    try:
        data = kwargs.pop("data", None)
        headers = headers or {}
        if json and not data:
            data = raw_dumps(json)
            headers["Content-Type"] = "application/json"
        r = request_session.request(  # type: ignore
            method,
            url,
            headers=headers,
            params=params,
            data=data,
            allow_redirects=allow_redirects,
            *args,
            **kwargs,
        )
        return Response(r)
    finally:
        if session is None:
            request_session.close()


def get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    session: Optional[requests.Session] = None,
    *args: Any,
    **kwargs: Any,
) -> Response:
    return request(
        "GET",
        url,
        params=params,
        headers=headers,
        session=session,
        *args,
        **kwargs,
    )


def post(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    json: Optional[Any] = None,
    session: Optional[requests.Session] = None,
    *args: Any,
    **kwargs: Any,
) -> Response:
    return request(
        "POST",
        url,
        params=params,
        headers=headers,
        json=json,
        session=session,
        *args,
        **kwargs,
    )


def put(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    json: Optional[Any] = None,
    session: Optional[requests.Session] = None,
    *args: Any,
    **kwargs: Any,
) -> Response:
    return request(
        "PUT",
        url,
        params=params,
        headers=headers,
        json=json,
        session=session,
        *args,
        **kwargs,
    )


def delete(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    session: Optional[requests.Session] = None,
    *args: Any,
    **kwargs: Any,
) -> Response:
    return request(
        "DELETE",
        url,
        params=params,
        headers=headers,
        session=session,
        *args,
        **kwargs,
    )
