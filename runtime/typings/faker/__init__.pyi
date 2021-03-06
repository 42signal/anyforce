from typing import Any, Optional, Tuple, Type

class Faker(object):
    def name(self) -> str: ...
    def pyint(
        self,
        min_value: Optional[int] = ...,
        max_value: Optional[int] = ...,
        step: Optional[int] = ...,
    ) -> int: ...
    def pystr(
        self, min_chars: Optional[int] = ..., max_chars: Optional[int] = ...
    ) -> str: ...
    def pytuple(
        self,
        nb_elements: Optional[int] = ...,
        variable_nb_elements: Optional[bool] = ...,
        value_types: Optional[Type[Any]] = ...,
        *allowed_types: Optional[Type[Any]],
    ) -> Tuple[Any, ...]: ...
    def url(self) -> str: ...
    def email(self) -> str: ...
