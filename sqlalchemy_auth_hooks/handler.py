import abc
from typing import Any, AsyncIterator

from sqlalchemy.orm import Mapper
from sqlalchemy.sql.roles import ExpressionElementRole

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


class ORMAuthHandler(abc.ABC):
    """
    Abstract class for ORM authorization checks
    """


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


class CoreAuthHandler(abc.ABC):
    """
    Abstract class for handling authorization of core database calls.
    """

    @abc.abstractmethod
    def before_select(
        self,
        session: AuthorizedSession,
        referenced_entities: list[ReferencedEntity],
        conditions: EntityConditions | None,
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        """
        Handle any select operations.
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


class AuthHandler(
    ORMAuthHandler,
    CoreAuthHandler,
    abc.ABC,
):
    """
    Abstract class for authorizing database calls.
    """
