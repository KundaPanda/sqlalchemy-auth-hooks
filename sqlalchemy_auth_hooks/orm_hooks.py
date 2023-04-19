import abc
import asyncio
from collections import defaultdict
from functools import partial
from threading import Thread
from typing import Any, Callable, Coroutine, TypeVar, cast

import structlog
from sqlalchemy import (
    event,
)
from sqlalchemy.orm import InstanceState, ORMExecuteState, Session, UOWTransaction, with_loader_criteria
from structlog.stdlib import BoundLogger

from sqlalchemy_auth_hooks.common_hooks import Hook
from sqlalchemy_auth_hooks.handler import SQLAlchemyAuthHandler
from sqlalchemy_auth_hooks.session import AuthorizedSession, check_skip
from sqlalchemy_auth_hooks.utils import collect_entities, run_loop

logger: BoundLogger = structlog.get_logger()

_O = TypeVar("_O")


class MutationHook(Hook[_O], abc.ABC):
    def __init__(self, state: InstanceState[_O]) -> None:
        self.state = state

    def __hash__(self) -> int:
        return hash(self.state)


class CreateHook(MutationHook[_O]):
    async def run(self, session: AuthorizedSession, handler: SQLAlchemyAuthHandler) -> None:
        logger.debug("Create hook called")
        await handler.after_single_create(session, self.state.object)


class DeleteHook(MutationHook[_O]):
    async def run(self, session: AuthorizedSession, handler: SQLAlchemyAuthHandler) -> None:
        logger.debug("Delete hook called")
        await handler.after_single_delete(session, self.state.object)


class _UpdateHook(MutationHook[_O]):
    def __init__(self, state: InstanceState[_O], changes: dict[str, Any]) -> None:
        super().__init__(state)
        self.changes = changes

    async def run(self, session: AuthorizedSession, handler: SQLAlchemyAuthHandler) -> None:
        logger.debug("Update hook called")
        await handler.after_single_update(session, self.state.object, self.changes)


T = TypeVar("T")


class ORMHooks:
    def __init__(self, handler: SQLAlchemyAuthHandler) -> None:
        self.handler = handler
        self._pending_hooks: dict[Session, dict[tuple[Any, ...] | None, list[Hook[Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._loop = asyncio.new_event_loop()
        self._executor_thread = Thread(target=partial(run_loop, self._loop), daemon=True)
        self._executor_thread.start()

    def call_async(self, func: Callable[..., Coroutine[T, None, Any]], *args: Any) -> T:
        future = asyncio.run_coroutine_threadsafe(func(*args), self._loop)
        return future.result()

    @staticmethod
    def _get_state_changes(state: InstanceState[Any]) -> dict[str, Any]:
        return {attr.key: attr.history.added[-1] for attr in state.attrs if attr.history.has_changes()}  # type: ignore

    def after_flush(self, session: Session, flush_context: UOWTransaction) -> None:
        logger.debug("after_flush")
        if check_skip(session):
            return
        for _mapper, states in flush_context.mappers.items():
            for state in states:
                if state.modified and state.has_identity and state.is_instance:
                    # Update
                    changes = self._get_state_changes(state)
                    self._pending_hooks[session][state.identity_key].append(_UpdateHook(state, changes))

    def after_flush_postexec(self, session: Session, flush_context: UOWTransaction) -> None:
        logger.debug("after_flush_postexec")
        if check_skip(session):
            return
        for _mapper, states in flush_context.mappers.items():
            for state in states:
                if not state.deleted and not state.detached and state.has_identity and state.is_instance:
                    # Create
                    self._pending_hooks[session][state.identity_key].append(CreateHook(state))
                elif state.deleted and state.has_identity and state.is_instance:
                    # Delete
                    self._pending_hooks[session][state.identity_key].append(DeleteHook(state))

    def after_commit(self, session: Session) -> None:
        logger.debug("after_commit")
        if check_skip(session):
            return
        if session not in self._pending_hooks:
            logger.debug("No tracked session states to process")
            return
        for pending_instance_key in self._pending_hooks[session]:
            for hook in self._pending_hooks[session][pending_instance_key]:
                self.call_async(hook.run, session, self.handler)
        del self._pending_hooks[session]

    def after_rollback(self, session: Session) -> None:
        logger.debug("after_rollback")
        if check_skip(session):
            return
        if session not in self._pending_hooks:
            logger.debug("No tracked session states to process")
            return
        del self._pending_hooks[session]

    def do_orm_execute(self, orm_execute_state: ORMExecuteState) -> None:
        logger.debug("do_orm_execute")
        if check_skip(orm_execute_state.session):
            return
        if orm_execute_state.is_select:
            entities, conditions = collect_entities(orm_execute_state)

            async def prepare_filters() -> None:
                async for selectable, filter_exp in self.handler.before_select(
                    cast(AuthorizedSession, orm_execute_state.session), entities, conditions
                ):
                    where_clause = with_loader_criteria(selectable, filter_exp, include_aliases=True)
                    orm_execute_state.statement = orm_execute_state.statement.options(where_clause)

            self.call_async(prepare_filters)
            return


def register_orm_hooks(handler: SQLAlchemyAuthHandler) -> None:
    """
    Register hooks for SQLAlchemy ORM events.
    """

    hooks = ORMHooks(handler)
    event.listen(Session, "after_flush", hooks.after_flush)
    event.listen(Session, "after_flush_postexec", hooks.after_flush_postexec)
    event.listen(Session, "after_commit", hooks.after_commit)
    event.listen(Session, "after_rollback", hooks.after_rollback)
    event.listen(Session, "do_orm_execute", hooks.do_orm_execute)
