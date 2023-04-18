import abc
from typing import Any

from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity


class SQLAlchemyAuthHandler(abc.ABC):
    """
    Abstract class for handling SQLAlchemy auth hook callbacks.
    """

    @abc.abstractmethod
    async def on_single_create(self, instance: Any) -> None:
        """
        Handle the creation of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def on_single_delete(self, instance: Any) -> None:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def on_single_update(self, instance: Any, changes: dict[str, Any]) -> None:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def on_select(self, referenced_entities: list[ReferencedEntity], conditions: EntityConditions | None) -> bool:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def on_update(
        self, referenced_entity: ReferencedEntity, conditions: EntityConditions | None, changes: dict[str, Any]
    ) -> None:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError
