import abc
from typing import Any, AsyncIterator

from sqlalchemy.orm import Mapper
from sqlalchemy.sql.roles import ExpressionElementRole

from sqlalchemy_auth_hooks.references import EntityCondition, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession


class AuthHandler(abc.ABC):
    """
    Abstract class for handling authorization of database calls.
    """

    @abc.abstractmethod
    def before_select(
        self,
        session: AuthorizedSession,
        referenced_entities: list[ReferencedEntity],
        condition: EntityCondition | None,
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        """
        Handle any select operations.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def before_insert(
        self,
        session: AuthorizedSession,
        entity: ReferencedEntity,
        values: list[dict[str, Any]],
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        """
        Handle any select operations.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def before_delete(
        self,
        session: AuthorizedSession,
        referenced_entities: list[ReferencedEntity],
        condition: EntityCondition | None,
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        """
        Handle any select operations.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def before_update(
        self,
        session: AuthorizedSession,
        referenced_entities: list[ReferencedEntity],
        condition: EntityCondition | None,
        changes: dict[str, Any],
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        """
        Handle any select operations.
        """
        raise NotImplementedError
