import abc
import asyncio
from collections import defaultdict
from typing import Any, Generic, TypeVar

import structlog
from sqlalchemy import event
from sqlalchemy.orm import InstanceState, Session, UOWTransaction
from structlog.stdlib import BoundLogger

from sqlalchemy_auth_hooks.handler import SQLAlchemyAuthHandler

logger: BoundLogger = structlog.get_logger()

_O = TypeVar("_O")


class _Hook(abc.ABC, Generic[_O]):
    def __init__(self, state: InstanceState[_O]) -> None:
        self.state = state

    @abc.abstractmethod
    async def run(self, handler: SQLAlchemyAuthHandler) -> None:
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(self.state)


class _CreateHook(_Hook[_O]):
    async def run(self, handler: SQLAlchemyAuthHandler) -> None:
        logger.debug("Create hook called")
        await handler.on_create(self.state.object)


class _DeleteHook(_Hook[_O]):
    async def run(self, handler: SQLAlchemyAuthHandler) -> None:
        logger.debug("Delete hook called")
        await handler.on_delete(self.state.object)


class _UpdateHook(_Hook[_O]):
    def __init__(self, state: InstanceState[_O], changes: dict[str, Any]) -> None:
        super().__init__(state)
        self.changes = changes

    async def run(self, handler: SQLAlchemyAuthHandler) -> None:
        logger.debug("Update hook called")
        await handler.on_update(self.state.object, self.changes)


class ORMHooks:
    def __init__(self, handler: SQLAlchemyAuthHandler) -> None:
        self.handler = handler
        self._tasks: set[asyncio.Task] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pending_hooks: dict[Session, dict[tuple[Any] | None, list[_Hook]]] = defaultdict(
            lambda: defaultdict(list)
        )

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop

    @staticmethod
    def _get_state_changes(state: InstanceState[_O]) -> dict[str, Any]:
        return {attr.key: attr.history.added[-1] for attr in state.attrs if attr.history.has_changes()}  # type: ignore

    def after_flush(self, session: Session, flush_context: UOWTransaction) -> None:
        logger.debug("after_flush")
        for _mapper, states in flush_context.mappers.items():
            for state in states:
                if state.modified and state.has_identity and state.is_instance:
                    # Update
                    changes = self._get_state_changes(state)
                    self._pending_hooks[session][state.identity_key].append(_UpdateHook(state, changes))

    def after_flush_postexec(self, session: Session, flush_context: UOWTransaction) -> None:
        logger.debug("after_flush_postexec")
        for _mapper, states in flush_context.mappers.items():
            for state in states:
                if not state.deleted and not state.detached and state.has_identity and state.is_instance:
                    # Create
                    self._pending_hooks[session][state.identity_key].append(_CreateHook(state))
                elif state.deleted and state.has_identity and state.is_instance:
                    # Delete
                    self._pending_hooks[session][state.identity_key].append(_DeleteHook(state))

    def after_commit(self, session: Session) -> None:
        logger.debug("after_commit")
        if session not in self._pending_hooks:
            logger.debug("No tracked session states to process")
            return
        for pending_instance_key in self._pending_hooks[session]:
            for hook in self._pending_hooks[session][pending_instance_key]:
                if self.loop.is_running():
                    task = self.loop.create_task(hook.run(self.handler))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.remove)
                else:
                    self.loop.run_until_complete(hook.run(self.handler))
        del self._pending_hooks[session]

    def after_rollback(self, session: Session) -> None:
        logger.debug("after_rollback")
        if session not in self._pending_hooks:
            logger.debug("No tracked session states to process")
            return
        del self._pending_hooks[session]


def _register_orm_hooks(handler: SQLAlchemyAuthHandler) -> None:
    """
    Register hooks for SQLAlchemy ORM events.
    """

    hooks = ORMHooks(handler)
    event.listen(Session, "after_flush", hooks.after_flush)
    event.listen(Session, "after_flush_postexec", hooks.after_flush_postexec)
    event.listen(Session, "after_commit", hooks.after_commit)
    event.listen(Session, "after_rollback", hooks.after_rollback)
