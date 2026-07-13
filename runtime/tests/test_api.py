from typing import Any

import orjson
import pytest
from fastapi import status

from anyforce.test import TestAPI as Base


class TestAPI(Base):
    @pytest.fixture()
    def endpoint(self, database: bool, router: Any):
        assert database
        assert router
        return "/models"

    def test_create(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "b",
                "required_char_field": self.faker.pystr(),
                "nullable_char_field": "unique",
                "int_field": self.faker.pyint(max_value=65565),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_201_CREATED,
        )

    def test_create_with_invalid_int(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "b",
                "required_char_field": self.faker.pystr(),
                "int_field": self.faker.name(),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_with_invalid_url(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "b",
                "required_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(max_value=65565),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.name(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_with_invalid_enum(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "c",
                "required_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(max_value=65565),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_with_duplicate_unique_field(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "a",
                "required_char_field": self.faker.pystr(),
                "nullable_char_field": "unique",
                "int_field": self.faker.pyint(max_value=65565),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_409_CONFLICT,
        )

    def test_create_without_required_field(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "a",
                "nullable_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(max_value=65565),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_with_too_long_field(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "a",
                "required_char_field": self.faker.pystr(min_chars=33, max_chars=64),
                "nullable_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(max_value=65565),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_related_object(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "a",
                "required_char_field": self.faker.pystr(),
                "nullable_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(max_value=65565),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_201_CREATED,
        )

    def test_create_another_related_object(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            {
                "char_enum_field": "a",
                "required_char_field": self.faker.pystr(),
                "nullable_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(max_value=65565),
                "bigint_field": self.faker.pyint(max_value=65565),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            },
            status.HTTP_201_CREATED,
        )

    def test_list_with_prefetch(self, client: Any, endpoint: str):
        def check_computed(params: dict[str, Any], response: Any) -> None:
            for item in response["data"]:
                assert (
                    item["int_field_plus_bigint_field"]
                    == item["int_field"] + item["bigint_field"]
                )
                assert (
                    item["async_int_field_plus_bigint_field"]
                    == item["int_field"] + item["bigint_field"]
                )

        self.list(
            client,
            endpoint,
            {
                "prefetch": [
                    "int_field_plus_bigint_field",
                    "async_int_field_plus_bigint_field",
                ],
                "order_by": "int_field",
            },
            status.HTTP_200_OK,
            check_computed,
        )

    def test_list_with_filter(self, client: Any, endpoint: str):
        def check_filtered(params: dict[str, Any], response: Any) -> None:
            assert response["total"] == 1
            assert response["data"][0]["char_enum_field"] == "b"

        self.list(
            client,
            endpoint,
            {"condition": [orjson.dumps({"char_enum_field": "b"}).decode()]},
            status.HTTP_200_OK,
            check_filtered,
        )

    def test_list_with_in_filter(self, client: Any, endpoint: str):
        def check_filtered(params: dict[str, Any], response: Any) -> None:
            assert response["total"] == 1
            assert response["data"][0]["char_enum_field"] == "b"

        self.list(
            client,
            endpoint,
            {"condition": [orjson.dumps({"char_enum_field.in": ["b"]}).decode()]},
            status.HTTP_200_OK,
            check_filtered,
        )

    def test_get(self, client: Any, endpoint: str):
        self.get(
            client,
            endpoint,
            {"id": 1, "prefetch": ["int_field_plus_bigint_field"]},
            status.HTTP_200_OK,
        )

    def test_get_not_found(self, client: Any, endpoint: str):
        self.get(
            client,
            endpoint,
            {"id": 10000},
            status.HTTP_404_NOT_FOUND,
        )

    def test_update(self, client: Any, endpoint: str):
        self.update(
            client,
            endpoint,
            {
                "id": 1,
                "prefetch": ["int_field_plus_bigint_field"],
                "body": {
                    "text_field": "hi@google.com",
                    "bigint_field": self.faker.pyint(max_value=65565),
                },
            },
            status.HTTP_200_OK,
        )

    def test_update_with_invalid_url(self, client: Any, endpoint: str):
        self.update(
            client,
            endpoint,
            {
                "id": 1,
                "prefetch": ["int_field_plus_bigint_field"],
                "body": {"text_field": self.faker.name()},
            },
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_related_object(self, client: Any, endpoint: str):
        self.update(
            client,
            endpoint,
            {
                "id": 2,
                "prefetch": ["int_field_plus_bigint_field"],
                "body": {"bigint_field": self.faker.pyint(max_value=65565)},
            },
            status.HTTP_200_OK,
        )

    def test_update_not_found(self, client: Any, endpoint: str):
        self.update(
            client,
            endpoint,
            {
                "id": 10000,
                "body": {"bigint_field": self.faker.pyint(max_value=65565)},
            },
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete(self, client: Any, endpoint: str):
        self.delete(
            client,
            endpoint,
            {"id": 1},
            status.HTTP_200_OK,
        )
