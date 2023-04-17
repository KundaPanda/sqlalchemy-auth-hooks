import abc
from typing import Generic, TypeVar

from sqlalchemy_auth_hooks.handler import SQLAlchemyAuthHandler

_O = TypeVar("_O")


class _Hook(abc.ABC, Generic[_O]):
    @abc.abstractmethod
    async def run(self, handler: SQLAlchemyAuthHandler) -> None:
        raise NotImplementedError
