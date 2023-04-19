import abc
from typing import Generic, TypeVar

from sqlalchemy_auth_hooks.handler import SQLAlchemyAuthHandler
from sqlalchemy_auth_hooks.session import AuthorizedSession

_O = TypeVar("_O")


class Hook(abc.ABC, Generic[_O]):
    @abc.abstractmethod
    async def run(self, session: AuthorizedSession, handler: SQLAlchemyAuthHandler) -> None:
        raise NotImplementedError  # pragma: no cover
