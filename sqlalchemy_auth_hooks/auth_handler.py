import abc
from typing import Any, AsyncIterator

from sqlalchemy.orm import Mapper
from sqlalchemy.sql.roles import ExpressionElementRole

from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession


class ORMAuthHandler(abc.ABC):
    """
    Abstract class for ORM authorization checks
    """


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


class AuthHandler(
    ORMAuthHandler,
    CoreAuthHandler,
    abc.ABC,
):
    """
    Abstract class for authorizing database calls.
    """
