"""
SQLAlchemy version compatibility tools.

Keep us compatible with multiple SQLAlchemy versions by implementing wrappers
when needed here.
"""
from typing import Any, Generator

from sqlalchemy.orm import DeclarativeMeta, registry


def iterate_model_classes(base_or_registry: registry | DeclarativeMeta) -> Generator[type[Any], None, None]:
    """
    Generate model classes that descend from a declarative base or exist in a registry.
    """
    if isinstance(base_or_registry, DeclarativeMeta):
        base_or_registry = base_or_registry.registry
    if not isinstance(base_or_registry, registry):
        raise TypeError("base_or_registry must be a DeclarativeMeta or registry")
    yield from (mapper.class_ for mapper in base_or_registry.mappers)
