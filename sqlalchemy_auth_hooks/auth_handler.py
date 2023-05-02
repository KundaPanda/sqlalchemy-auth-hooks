import abc
from typing import Any, AsyncIterator, Iterable

from sqlalchemy.orm import Mapper
from sqlalchemy.sql.roles import ExpressionElementRole

from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession


class AuthHandler(abc.ABC):
    """
    Abstract class for handling authorization of database calls.
    """

    @abc.abstractmethod
    def before_select(
        self,
        session: AuthorizedSession,
        referenced_entities: Iterable[ReferencedEntity],
        conditions: EntityConditions | None,
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        """
        Handle any select operations.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def before_update(
        self,
        session: AuthorizedSession,
        referenced_entities: Iterable[ReferencedEntity],
        conditions: EntityConditions | None,
        changes: dict[str, Any],
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        """
        Handle any select operations.
        """
        raise NotImplementedError
