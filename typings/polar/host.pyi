"""
This type stub file was generated by pyright.
"""

from dataclasses import dataclass
from typing import Any, Dict, Union, Callable

from typings.polar import Polar

"""Translate between Polar and the host language (Python)."""

@dataclass
class UserType:
    name: str
    cls: type
    id: int
    fields: Dict[str, Any]
    ...

class Host:
    """Maintain mappings and caches for Python classes & instances."""

    types: Dict[Union[str, type], UserType]
    def __init__(
        self,
        polar: Polar,
        types: dict[str | type[Any], UserType] | None = ...,
        instances: dict[int, type[Any]] | None = ...,
        get_field: Callable[[type[Any], str], Any] | None = ...,
        adapter: None = ...,
    ) -> None:
        self.get_field: Callable[[type[Any], str], Any] = ...
        self.types: dict[str | type[Any], UserType] = ...
        self.instances: dict[int, type[Any]] = ...
    def types_get_field(self, obj, field) -> type: ...
    def copy(self) -> Host:
        """Copy an existing cache."""
        ...
    def get_class(self, name):  # -> type:
        """Fetch a Python class from the cache."""
        ...
    def distinct_user_types(self): ...
    def cache_class(self, cls, name=..., fields=...):
        """Cache Python class by name."""
        ...
    def register_mros(self) -> None:
        """Register the MRO of each registered class to be used for rule type validation."""
        ...
    def get_instance(self, id):  # -> Any:
        """Look up Python instance by id."""
        ...
    def cache_instance(self, instance, id=...):
        """Cache Python instance under Polar-generated id."""
        ...
    def make_instance(self, name, args, kwargs, id):
        """Construct and cache a Python instance."""
        ...
    def unify(self, left_instance_id, right_instance_id) -> bool:
        """Return true if the left instance is equal to the right."""
        ...
    def isa(self, instance, class_tag) -> bool: ...
    def isa_with_path(self, base_tag, path, class_tag) -> bool: ...
    def is_subclass(self, left_tag, right_tag) -> bool:
        """Return true if left is a subclass (or the same class) as right."""
        ...
    def is_subspecializer(self, instance_id, left_tag, right_tag) -> bool:
        """Return true if the left class is more specific than the right class
        with respect to the given instance."""
        ...
    def operator(self, op, args): ...
    def enrich_message(self, message: str) -> str:
        """
        "Enrich" a message from the polar core, such as a log line, debug
        message, or error trace.

        Currently only used to enrich messages with instance reprs. This allows
        us to avoid sending reprs eagerly when an instance is created in polar.
        """
        ...
    def to_polar(
        self, v
    ):  # -> dict[str, dict[str, bool] | dict[str, dict[str, int]] | dict[str, dict[str, float | str]] | dict[str, str] | dict[str, list[Unknown]] | dict[str, dict[str, dict[Unknown, Unknown]]] | dict[str, dict[str, str | list[Unknown]]] | dict[str, Variable] | dict[str, dict[str, Unknown | list[Unknown]]] | dict[str, Unknown] | dict[str, dict[str, dict[str, Unknown]]] | dict[str, dict[str, Unknown | int | str | None]]]:
        """Convert a Python object to a Polar term."""
        ...
    def to_python(
        self, value
    ):  # -> float | list[Unknown] | dict[Unknown, Unknown] | Any | Predicate | Variable | Expression | Pattern:
        """Convert a Polar term to a Python object."""
        ...
    def set_accept_expression(self, accept):  # -> None:
        """Set whether the Host accepts Expression types from Polar, or raises an error."""
        ...
