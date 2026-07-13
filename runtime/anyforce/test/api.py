import logging
from functools import cached_property
from typing import Any, Callable, Iterable, cast

from faker import Faker
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from .request import delete, get, post, put

logger = logging.getLogger()


TestConfigs = Iterable[
    tuple[
        dict[str, Any],
        int,
        Callable[[dict[str, Any], Any], None] | None,
    ]
]


class TestAPI:
    @cached_property
    def faker(self) -> Faker:
        return Faker()

    def create(
        self,
        client: TestClient,
        endpoint: str,
        json: dict[str, Any],
        status_code: int,
        callback: Callable[[dict[str, Any], Any], None] | None = None,
    ) -> dict[str, Any]:
        r = post(client, endpoint, json=json)
        self.log_request(json, status_code, r)

        obj = r.json_object()
        if status_code < 300:
            self.assert_obj(obj)
            self.log_compare(obj, jsonable_encoder(json))

        if callback:
            callback(json, obj)
        return obj

    def list(
        self,
        client: TestClient,
        endpoint: str,
        params: dict[str, Any],
        status_code: int,
        callback: Callable[[dict[str, Any], Any], None] | None = None,
    ) -> dict[str, Any]:
        r = get(client, f"{endpoint}/", params=params)
        self.log_request(params, status_code, r)

        obj = r.json_object()
        if status_code < 300:
            # validate total offset limit
            assert obj
            assert obj["total"] > 0
            assert len(obj["data"]) > 0 and len(obj["data"]) < params.get("limit", 20)
            assert params.get("offset", 0) + len(obj["data"]) <= obj["total"]

            self.assert_obj(obj["data"][0])

            # validate prefetch
            prefetch: Any = params.get("prefetch", [])
            prefetch = (
                cast(list[str], prefetch) if isinstance(prefetch, list) else [prefetch]
            )
            for k in prefetch:
                exist = False
                for e in obj["data"]:
                    if e.get(k) is not None:
                        exist = True
                        break
                if not exist:
                    logger.info(f"prefetch: {prefetch} => {obj['data']}")
                assert exist

        if callback:
            callback(params, obj)
        return obj

    def get(
        self,
        client: TestClient,
        endpoint: str,
        params: dict[str, Any],
        status_code: int,
        callback: Callable[[dict[str, Any], Any], None] | None = None,
    ) -> dict[str, Any]:
        input_params = params.copy()
        r = get(
            client,
            f"{endpoint}/{params.pop('id')}",
            params=params,
        )
        self.log_request(input_params, status_code, r)

        obj = r.json_object()
        if status_code < 300:
            self.assert_obj(obj)

            # validate prefetch
            prefetch: Any = params.get("prefetch", [])
            prefetch = (
                cast(list[str], prefetch) if isinstance(prefetch, list) else [prefetch]
            )
            for k in prefetch:
                assert obj.get(k) is not None

        if callback:
            callback(params, obj)
        return obj

    def update(
        self,
        client: TestClient,
        endpoint: str,
        params: dict[str, Any],
        status_code: int,
        callback: Callable[[dict[str, Any], Any], None] | None = None,
    ) -> dict[str, Any]:
        input_params = params.copy()
        body = params.pop("body", {})
        r = put(
            client,
            f"{endpoint}/{params.pop('id')}",
            json=body,
            params=params,
        )
        self.log_request(input_params, status_code, r)

        obj = r.json_object()
        if status_code < 300:
            self.assert_obj(obj)
            self.log_compare(obj, body)

        if callback:
            callback(params, obj)
        return obj

    def delete(
        self,
        client: TestClient,
        endpoint: str,
        params: dict[str, Any],
        status_code: int,
        callback: Callable[[dict[str, Any], Any], None] | None = None,
    ) -> dict[str, Any]:
        input_params = params.copy()
        r = delete(
            client,
            f"{endpoint}/{params.pop('id')}",
            params=params,
        )
        self.log_request(input_params, status_code, r)

        obj = r.json_object()
        if status_code < 300:
            assert obj
            assert obj["id"]

        if callback:
            callback(params, obj)
        return obj

    @staticmethod
    def log_request(input: Any, status_code: int, r: Any):
        logging.info(
            f"expect: {status_code}, request: {input} -> [{r.status_code}]{r.text}",
            stack_info=True,
        )
        assert r.status_code == status_code

    @staticmethod
    def assert_obj(obj: Any):
        assert obj
        assert obj["id"]
        assert obj["created_at"]
        assert obj["updated_at"]

    @staticmethod
    def log_compare(lv: Any, rv: Any):
        diff: dict[str, Any] = {}
        r = TestAPI.compare(lv, rv, "", diff)
        if not r:
            logger.info(f"not equal: {diff}")

    @staticmethod
    def compare(lv: Any, rv: Any, path: str, diff: dict[str, Any]):
        if isinstance(lv, dict) and isinstance(rv, dict):
            lv = cast(dict[str, Any], lv)
            rv = cast(dict[str, Any], rv)
            for k, v in rv.items():
                if not TestAPI.compare(lv.get(k), v, f"{path}.{k}", diff):
                    return False
            return True
        if isinstance(lv, list) and isinstance(rv, list):
            rv = cast(list[Any], rv)
            for i, v in enumerate(rv):
                if not TestAPI.compare(lv[i], v, f"{path}.{i}", diff):
                    return False
            return True
        if lv == rv:
            return True
        diff[path] = (lv, rv)
        return False
