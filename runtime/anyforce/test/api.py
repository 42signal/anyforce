import logging
from functools import cached_property
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, cast

from faker import Faker
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from .request import delete, get, post, put

logger = logging.getLogger()


TestConfigs = Iterable[
    Tuple[
        Dict[str, Any],
        int,
        Optional[Callable[[Dict[str, Any], Any], None]],
    ]
]


class TestAPI:
    @cached_property
    def faker(self) -> Faker:
        return Faker()

    def test_create(
        self,
        client: TestClient,
        database: bool,
        router: APIRouter,
        endpoint: str,
        create_tests: TestConfigs,
    ):
        assert router
        assert database
        for json, status_code, callback in create_tests:
            r = post(client, endpoint, json=json)
            self.log_request(json, status_code, r)

            obj = r.json_object()
            if status_code < 300:
                self.assert_obj(obj)
                self.log_compare(obj, jsonable_encoder(json))

            if callback:
                callback(json, obj)

    def test_list(
        self,
        client: TestClient,
        database: bool,
        router: APIRouter,
        endpoint: str,
        list_tests: TestConfigs,
    ):
        assert router
        assert database
        for params, status_code, callback in list_tests:
            r = get(client, endpoint, params=params)
            self.log_request(params, status_code, r)

            r = r.json_object()
            if status_code < 300:
                # validate total offset limit
                assert r
                assert r["total"] > 0
                assert len(r["data"]) > 0 and len(r["data"]) < params.get("limit", 20)
                assert params.get("offset", 0) + len(r["data"]) <= r["total"]

                self.assert_obj(r["data"][0])

                # validate prefetch
                prefetch: Any = params.get("prefetch", [])
                prefetch = prefetch if isinstance(prefetch, list) else [prefetch]
                for k in prefetch:
                    exist = False
                    for e in r["data"]:
                        if e.get(k) is not None:
                            exist = True
                            break
                    if not exist:
                        logger.info(f"prefetch: {prefetch} => {r['data']}")
                    assert exist

            if callback:
                callback(params, r)

    def test_get(
        self,
        client: TestClient,
        database: bool,
        router: APIRouter,
        endpoint: str,
        get_tests: TestConfigs,
    ):
        assert router
        assert database
        for params, status_code, callback in get_tests:
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

                # validate preftch
                prefetch: Any = params.get("prefetch", [])
                prefetch = prefetch if isinstance(prefetch, list) else [prefetch]
                for k in prefetch:
                    assert obj.get(k) is not None

            if callback:
                callback(params, obj)

    def test_update(
        self,
        client: TestClient,
        database: bool,
        router: APIRouter,
        endpoint: str,
        update_tests: TestConfigs,
    ):
        assert router
        assert database
        for params, status_code, callback in update_tests:
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

    def test_delete(
        self,
        client: TestClient,
        database: bool,
        router: APIRouter,
        endpoint: str,
        delete_tests: TestConfigs,
    ):
        assert router
        assert database
        for params, status_code, callback in delete_tests:
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

    @staticmethod
    def log_request(input: Any, status_code: int, r: Any):
        if r.status_code != status_code:
            logging.info(
                f"expect: {status_code}, request: {input} -> [{r.status_code}]{r.text}"
            )
            breakpoint()
        assert r.status_code == status_code

    @staticmethod
    def assert_obj(obj: Any):
        assert obj
        assert obj["id"]
        assert obj["created_at"]
        assert obj["updated_at"]

    @staticmethod
    def log_compare(lv: Any, rv: Any):
        diff: Dict[str, Any] = {}
        r = TestAPI.compare(lv, rv, "", diff)
        if not r:
            logger.info(f"not equal: {diff}")
        assert r

    @staticmethod
    def compare(lv: Any, rv: Any, path: str, diff: Dict[str, Any]):
        if isinstance(lv, dict) and isinstance(rv, dict):
            lv = cast(Dict[str, Any], lv)
            rv = cast(Dict[str, Any], rv)
            for k, v in rv.items():
                if not TestAPI.compare(lv.get(k), v, f"{path}.{k}", diff):
                    return False
            return True
        if isinstance(lv, list) and isinstance(rv, list):
            rv = cast(List[Any], rv)
            for i, v in enumerate(rv):
                if not TestAPI.compare(lv[i], v, f"{path}.{i}", diff):
                    return False
            return True
        if lv == rv:
            return True
        diff[path] = (lv, rv)
        return False
