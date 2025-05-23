from typing import Any, Callable
from urllib.parse import urlencode, urljoin

import aiohttp
from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

from ... import json
from ..exceptions import HTTPUnAuthorizedError


class OAuth2(object):
    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        scheme: str | None = None,
    ):
        super().__init__()
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scheme = scheme

    def join(self, path: str, q: dict[str, str] = {}):
        return f"{urljoin(self.base_url, path)}?{urlencode(q)}"

    def redirect_url(self, request: Request, redirect_uri: str):
        base = str(
            request.url.replace(scheme=self.scheme) if self.scheme else request.url
        )
        url = f"{urljoin(base, 'auth')}?{urlencode({'redirect_uri': redirect_uri})}"
        return url

    def auth_url(self, redirect_uri: str):
        return self.join(
            "auth",
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": "openid",
            },
        )

    async def auth(self, code: str, redirect_uri: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.join("token"),
                data=aiohttp.FormData(
                    {
                        "client_id": "dashboard",
                        "client_secret": "f1ace9da-0d6a-4532-938d-8c8ea7730487",
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                    }
                ),
            ) as response:
                r = await response.json(loads=json.loads)
                return r["access_token"], r["id_token"]

    async def userinfo(self, token: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.join("userinfo"), headers={"Authorization": f"Bearer {token}"}
            ) as response:
                return await response.json(loads=json.loads)

    def bind(
        self,
        router: APIRouter,
        wrap: bool,
        verify: Callable[[Request, Any, str], Any],
        post_logout_redirect_uri: str = "",
    ):
        @router.get("/login")
        def login(request: Request, redirect_uri: str = ""):
            redirect_uri = (
                self.redirect_url(request, redirect_uri)
                if not redirect_uri or wrap
                else redirect_uri
            )
            return RedirectResponse(self.auth_url(redirect_uri))

        @router.get("/auth")
        async def auth(request: Request, code: str, redirect_uri: str = ""):
            token, id_token = await self.auth(
                code,
                (
                    self.redirect_url(request, redirect_uri)
                    if not redirect_uri or wrap
                    else redirect_uri
                ),
            )
            r = await verify(request, await self.userinfo(token), redirect_uri)
            if not r:
                return HTTPUnAuthorizedError
            request.session["id_token"] = id_token
            return r

        @router.get("/logout")
        def logout(request: Request):
            params: dict[str, str] = {
                "client_id": self.client_id,
                "post_logout_redirect_uri": post_logout_redirect_uri,
            }
            id_token = request.session.get("id_token", "")
            if id_token:
                params["id_token_hint"] = id_token
            return RedirectResponse(self.join("logout", params))

        return login, auth, logout
