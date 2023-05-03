import abc
from typing import Any

from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession


class PostAuthHandler(abc.ABC):
    """
    Abstract class with post authorization callbacks (i.e. for update propagation)
    """

    @abc.abstractmethod
    async def after_single_insert(self, session: AuthorizedSession, instance: Any) -> None:
        """
        Handle the creation of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def after_single_delete(self, session: AuthorizedSession, instance: Any) -> None:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def after_single_update(self, session: AuthorizedSession, instance: Any, changes: dict[str, Any]) -> None:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def after_many_insert(
        self,
        session: AuthorizedSession,
        entity: ReferencedEntity,
        values: list[dict[str, Any]],
    ) -> None:
        """
        Handle the creation of multiple SQLAlchemy models.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def after_many_delete(
        self,
        session: AuthorizedSession,
        entity: ReferencedEntity,
        conditions: EntityConditions | None,
    ) -> None:
        """
        Handle the deletion of multiple SQLAlchemy models.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def after_many_update(
        self,
        session: AuthorizedSession,
        entity: ReferencedEntity,
        conditions: EntityConditions | None,
        changes: dict[str, Any],
    ) -> None:
        """
        Handle the update of multiple SQLAlchemy models.
        """
        raise NotImplementedError
