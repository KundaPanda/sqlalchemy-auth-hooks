import abc
from typing import Any, AsyncIterator

from sqlalchemy.orm import Mapper
from sqlalchemy.sql.roles import ExpressionElementRole

from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession


class SQLAlchemyORMHandler(abc.ABC):
    """
    Abstract class for handling SQLAlchemy ORM hook callbacks.
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


class SQLAlchemyCoreHandler(abc.ABC):
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


class SQLAlchemyAuthHandler(
    SQLAlchemyORMHandler,
    SQLAlchemyCoreHandler,
    abc.ABC,
):
    """
    Abstract class for handling SQLAlchemy auth hook callbacks.
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
