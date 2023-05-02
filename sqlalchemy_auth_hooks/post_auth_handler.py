import abc
from typing import Any

from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession


class ORMPostAuthHandler(abc.ABC):
    """
    Abstract class with post authorization hooks (i.e. for update propagation)
    """

    @abc.abstractmethod
    async def after_single_create(self, session: AuthorizedSession, instance: Any) -> None:
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


class CorePostAuthHandler(abc.ABC):
    """
    Abstract class for handling SQLAlchemy Core hook callbacks.
    """

    @abc.abstractmethod
    async def after_core_update(
        self,
        session: AuthorizedSession,
        referenced_entity: ReferencedEntity,
        conditions: EntityConditions | None,
        changes: dict[str, Any],
    ) -> None:
        """
        Handle the deletion of an SQLAlchemy model.
        """
        raise NotImplementedError


class PostAuthHandler(
    ORMPostAuthHandler,
    CorePostAuthHandler,
    abc.ABC,
):
    """
    Abstract class for handling events after their processing (i.e. for state update propagation).
    """
