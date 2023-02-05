from typing import Any, Dict

import pytest
from fastapi import status

from anyforce.json import fast_dumps
from anyforce.test import TestAPI as Base


class TestAPI(Base):
    @pytest.fixture()
    def endpoint(self):
        yield "/models"

    @pytest.fixture()
    def create_tests(self):
        def tests():
            unique_field = self.faker.pystr()
            yield {
                "char_enum_field": "b",
                "required_char_field": self.faker.pystr(),
                "nullable_char_field": unique_field,
                "int_field": self.faker.pyint(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_201_CREATED, None

            # int
            yield {
                "char_enum_field": "b",
                "required_char_field": self.faker.pystr(),
                "int_field": self.faker.name(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_400_BAD_REQUEST, None

            # url
            yield {
                "char_enum_field": "b",
                "required_char_field": self.faker.pystr(),
                "int_field": self.faker.name(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.name(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_400_BAD_REQUEST, None

            # enum
            yield {
                "char_enum_field": "c",
                "required_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_400_BAD_REQUEST, None

            # unique
            yield {
                "char_enum_field": "a",
                "required_char_field": self.faker.pystr(),
                "nullable_char_field": unique_field,
                "int_field": self.faker.pyint(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_409_CONFLICT, None

            # required
            yield {
                "char_enum_field": "a",
                "nullable_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_400_BAD_REQUEST, None

            # too lang
            yield {
                "char_enum_field": "a",
                "required_char_field": self.faker.pystr(min_chars=33, max_chars=64),
                "nullable_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_400_BAD_REQUEST, None

            # save related
            yield {
                "char_enum_field": "a",
                "required_char_field": self.faker.pystr(),
                "nullable_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_201_CREATED, None
            yield {
                "char_enum_field": "a",
                "required_char_field": self.faker.pystr(),
                "nullable_char_field": self.faker.pystr(),
                "int_field": self.faker.pyint(),
                "bigint_field": self.faker.pyint(),
                "text_field": self.faker.url(),
                "json_field": list(self.faker.pytuple()),
            }, status.HTTP_201_CREATED, None

        return tests()

    @pytest.fixture()
    def list_tests(self):
        def check_computed(params: Dict[str, Any], r: Any) -> None:
            for e in r["data"]:
                assert (
                    e["int_field_plus_bigint_field"]
                    == e["int_field"] + e["bigint_field"]
                )
                assert (
                    e["async_int_field_plus_bigint_field"]
                    == e["int_field"] + e["bigint_field"]
                )

        def tests():
            # prefetch / computed / order_by
            yield {
                "prefetch": [
                    "int_field_plus_bigint_field",
                    "async_int_field_plus_bigint_field",
                ],
                "order_by": "int_field",
            }, status.HTTP_200_OK, check_computed

            def check1(params: Dict[str, Any], r: Any) -> None:
                assert r["total"] == 1
                assert r["data"][0]["char_enum_field"] == "b"

            # filter
            yield {
                "condition": [fast_dumps({"char_enum_field": "b"})]
            }, status.HTTP_200_OK, check1

            yield {
                "condition": [fast_dumps({"char_enum_field.in": ["b"]})]
            }, status.HTTP_200_OK, check1

        return tests()

    @pytest.fixture()
    def get_tests(self):
        def tests():
            yield {
                "id": 1,
                "prefetch": ["int_field_plus_bigint_field"],
            }, status.HTTP_200_OK, None
            yield {"id": 10000}, status.HTTP_404_NOT_FOUND, None

        return tests()

    @pytest.fixture()
    def update_tests(self):
        def tests():
            yield {
                "id": 1,
                "prefetch": ["int_field_plus_bigint_field"],
                "body": {
                    "text_field": "hi@google.com",
                    "bigint_field": self.faker.pyint(),
                },
            }, status.HTTP_200_OK, None

            yield {
                "id": 1,
                "prefetch": ["int_field_plus_bigint_field"],
                "body": {"text_field": self.faker.name()},
            }, status.HTTP_400_BAD_REQUEST, None

            yield {
                "id": 2,
                "prefetch": ["int_field_plus_bigint_field"],
                "body": {"bigint_field": self.faker.pyint()},
            }, status.HTTP_200_OK, None

            yield {
                "id": 10000,
                "body": {
                    "bigint_field": self.faker.pyint(),
                },
            }, status.HTTP_404_NOT_FOUND, None

        return tests()

    @pytest.fixture()
    def delete_tests(self):
        def tests():
            yield {"id": 1}, status.HTTP_200_OK, None

        return tests()
