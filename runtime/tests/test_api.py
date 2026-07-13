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

    def create_data(self, **overrides: Any) -> dict[str, Any]:
        data = {
            "char_enum_field": "a",
            "required_char_field": self.faker.pystr(),
            "nullable_char_field": self.faker.pystr(),
            "int_field": self.faker.pyint(max_value=65565),
            "bigint_field": self.faker.pyint(max_value=65565),
            "text_field": self.faker.url(),
            "json_field": list(self.faker.pytuple()),
        }
        data.update(overrides)
        return data

    def test_create(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            self.create_data(char_enum_field="b"),
            status.HTTP_201_CREATED,
        )

    def test_create_with_invalid_int(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            self.create_data(char_enum_field="b", int_field=self.faker.name()),
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_with_invalid_url(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            self.create_data(char_enum_field="b", text_field=self.faker.name()),
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_with_invalid_enum(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            self.create_data(char_enum_field="c"),
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_with_duplicate_unique_field(self, client: Any, endpoint: str):
        unique_field = self.faker.pystr()
        self.create(
            client,
            endpoint,
            self.create_data(nullable_char_field=unique_field),
            status.HTTP_201_CREATED,
        )
        self.create(
            client,
            endpoint,
            self.create_data(nullable_char_field=unique_field),
            status.HTTP_409_CONFLICT,
        )

    def test_create_without_required_field(self, client: Any, endpoint: str):
        data = self.create_data()
        del data["required_char_field"]
        self.create(client, endpoint, data, status.HTTP_400_BAD_REQUEST)

    def test_create_with_too_long_field(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            self.create_data(
                required_char_field=self.faker.pystr(min_chars=33, max_chars=64)
            ),
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_related_object(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            self.create_data(),
            status.HTTP_201_CREATED,
        )

    def test_create_another_related_object(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            self.create_data(),
            status.HTTP_201_CREATED,
        )

    def test_list_with_prefetch(self, client: Any, endpoint: str):
        self.create(client, endpoint, self.create_data(), status.HTTP_201_CREATED)

        def check_computed(_params: dict[str, Any], response: Any) -> None:
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
        self.create(
            client,
            endpoint,
            self.create_data(char_enum_field="b"),
            status.HTTP_201_CREATED,
        )

        def check_filtered(_params: dict[str, Any], response: Any) -> None:
            assert all(item["char_enum_field"] == "b" for item in response["data"])

        self.list(
            client,
            endpoint,
            {"condition": [orjson.dumps({"char_enum_field": "b"}).decode()]},
            status.HTTP_200_OK,
            check_filtered,
        )

    def test_list_with_in_filter(self, client: Any, endpoint: str):
        self.create(
            client,
            endpoint,
            self.create_data(char_enum_field="b"),
            status.HTTP_201_CREATED,
        )

        def check_filtered(_params: dict[str, Any], response: Any) -> None:
            assert all(item["char_enum_field"] == "b" for item in response["data"])

        self.list(
            client,
            endpoint,
            {"condition": [orjson.dumps({"char_enum_field.in": ["b"]}).decode()]},
            status.HTTP_200_OK,
            check_filtered,
        )

    def test_get(self, client: Any, endpoint: str):
        created = self.create(
            client, endpoint, self.create_data(), status.HTTP_201_CREATED
        )
        self.get(
            client,
            endpoint,
            {"id": created["id"], "prefetch": ["int_field_plus_bigint_field"]},
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
        created = self.create(
            client, endpoint, self.create_data(), status.HTTP_201_CREATED
        )
        self.update(
            client,
            endpoint,
            {
                "id": created["id"],
                "prefetch": ["int_field_plus_bigint_field"],
                "body": {
                    "text_field": "hi@google.com",
                    "bigint_field": self.faker.pyint(max_value=65565),
                },
            },
            status.HTTP_200_OK,
        )

    def test_update_with_invalid_url(self, client: Any, endpoint: str):
        created = self.create(
            client, endpoint, self.create_data(), status.HTTP_201_CREATED
        )
        self.update(
            client,
            endpoint,
            {
                "id": created["id"],
                "prefetch": ["int_field_plus_bigint_field"],
                "body": {"text_field": self.faker.name()},
            },
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_related_object(self, client: Any, endpoint: str):
        created = self.create(
            client, endpoint, self.create_data(), status.HTTP_201_CREATED
        )
        self.update(
            client,
            endpoint,
            {
                "id": created["id"],
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
        created = self.create(
            client, endpoint, self.create_data(), status.HTTP_201_CREATED
        )
        self.delete(
            client,
            endpoint,
            {"id": created["id"]},
            status.HTTP_200_OK,
        )
