import abc
from typing import Any

from sqlalchemy.orm import Mapper


class ReferencedEntity:
    def __init__(self, entity: Mapper, keys: dict[str, Any] | None = None) -> None:
        self.entity = entity
        self.keys = keys or {}


class SQLAlchemyAuthHandler(abc.ABC):
    """
    Abstract class for handling SQLAlchemy auth hook callbacks.
    """

    @abc.abstractmethod
    async def on_create(self, instance: Any) -> None:
        """
        Handle the creation of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def on_delete(self, instance: Any) -> None:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def on_update(self, instance: Any, changes: dict[str, Any]) -> None:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def on_select(self, instance: Any) -> bool:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError
