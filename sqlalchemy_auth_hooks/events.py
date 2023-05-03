import abc
from typing import Any, Generic, TypeVar

import structlog
from sqlalchemy.orm import InstanceState

from sqlalchemy_auth_hooks.post_auth_handler import PostAuthHandler
from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession

logger = structlog.get_logger()

_O = TypeVar("_O")


class Event(abc.ABC, Generic[_O]):
    @abc.abstractmethod
    async def trigger(self, session: AuthorizedSession, handler: PostAuthHandler) -> None:
        raise NotImplementedError  # pragma: no cover


class SingleMutationEvent(Event[_O], abc.ABC):
    def __init__(self, state: InstanceState[_O]) -> None:
        self.state = state

    def __hash__(self) -> int:
        return hash(self.state)


class ManyMutationEvent(Event[_O], abc.ABC):
    def __init__(self, entity: ReferencedEntity) -> None:
        self.entity = entity

    def __hash__(self) -> int:
        return hash(self.entity)


class CreateSingleEvent(SingleMutationEvent[_O]):
    async def trigger(self, session: AuthorizedSession, handler: PostAuthHandler) -> None:
        logger.debug("Create event triggered")
        await handler.after_single_insert(session, self.state.object)


class DeleteSingleEvent(SingleMutationEvent[_O]):
    async def trigger(self, session: AuthorizedSession, handler: PostAuthHandler) -> None:
        logger.debug("Delete event triggered")
        await handler.after_single_delete(session, self.state.object)


class UpdateSingleEvent(SingleMutationEvent[_O]):
    def __init__(self, state: InstanceState[_O], changes: dict[str, Any]) -> None:
        super().__init__(state)
        self.changes = changes

    async def trigger(self, session: AuthorizedSession, handler: PostAuthHandler) -> None:
        logger.debug("Update event triggered")
        await handler.after_single_update(session, self.state.object, self.changes)


class CreateManyEvent(ManyMutationEvent[_O]):
    def __init__(self, entity: ReferencedEntity, values: list[dict[str, Any]]) -> None:
        super().__init__(entity)
        self.values = values

    async def trigger(self, session: AuthorizedSession, handler: PostAuthHandler) -> None:
        logger.debug("Create many event triggered")
        await handler.after_many_insert(session, self.entity, self.values)


class DeleteManyEvent(ManyMutationEvent[_O]):
    def __init__(self, entity: ReferencedEntity, conditions: EntityConditions | None) -> None:
        super().__init__(entity)
        self.conditions = conditions

    async def trigger(self, session: AuthorizedSession, handler: PostAuthHandler) -> None:
        logger.debug("Delete many event triggered")
        await handler.after_many_delete(session, self.entity, self.conditions)


class UpdateManyEvent(ManyMutationEvent[_O]):
    def __init__(self, entity: ReferencedEntity, conditions: EntityConditions | None, changes: dict[str, Any]) -> None:
        super().__init__(entity)
        self.conditions = conditions
        self.changes = changes

    async def trigger(self, session: AuthorizedSession, handler: PostAuthHandler) -> None:
        logger.debug("Update many event triggered")
        await handler.after_many_update(session, self.entity, self.conditions, self.changes)
