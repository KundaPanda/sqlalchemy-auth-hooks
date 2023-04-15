import abc
import asyncio
from collections import defaultdict
from typing import Any, Generic, TypeVar

import structlog
from asgiref.sync import async_to_sync
from sqlalchemy import BinaryExpression, BindParameter, BooleanClauseList, ColumnClause, Select, Table, event
from sqlalchemy.orm import InstanceState, Mapper, ORMExecuteState, Session, UOWTransaction
from structlog.stdlib import BoundLogger

from sqlalchemy_auth_hooks.handler import ReferencedEntity, SQLAlchemyAuthHandler

logger: BoundLogger = structlog.get_logger()

_O = TypeVar("_O")


class _Hook(abc.ABC, Generic[_O]):
    @abc.abstractmethod
    async def run(self, handler: SQLAlchemyAuthHandler) -> None:
        raise NotImplementedError


class _MutationHook(_Hook[_O], abc.ABC):
    def __init__(self, state: InstanceState[_O]) -> None:
        self.state = state

    def __hash__(self) -> int:
        return hash(self.state)


class _CreateHook(_MutationHook[_O]):
    async def run(self, handler: SQLAlchemyAuthHandler) -> None:
        logger.debug("Create hook called")
        await handler.on_create(self.state.object)


class _DeleteHook(_MutationHook[_O]):
    async def run(self, handler: SQLAlchemyAuthHandler) -> None:
        logger.debug("Delete hook called")
        await handler.on_delete(self.state.object)


class _UpdateHook(_MutationHook[_O]):
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
                async_to_sync(hook.run)(self.handler)
        del self._pending_hooks[session]

    def after_rollback(self, session: Session) -> None:
        logger.debug("after_rollback")
        if session not in self._pending_hooks:
            logger.debug("No tracked session states to process")
            return
        del self._pending_hooks[session]

    def do_orm_execute(self, orm_execute_state: ORMExecuteState) -> None:
        logger.debug("do_orm_execute")
        if orm_execute_state.is_select:
            entities = _collect_entities(orm_execute_state)
            for entity in entities:
                async_to_sync(self.handler.on_select)(entity)


def _register_orm_hooks(handler: SQLAlchemyAuthHandler) -> None:
    """
    Register hooks for SQLAlchemy ORM events.
    """

    hooks = ORMHooks(handler)
    event.listen(Session, "after_flush", hooks.after_flush)
    event.listen(Session, "after_flush_postexec", hooks.after_flush_postexec)
    event.listen(Session, "after_commit", hooks.after_commit)
    event.listen(Session, "after_rollback", hooks.after_rollback)
    event.listen(Session, "do_orm_execute", hooks.do_orm_execute)


def _process_condition(
    condition: BinaryExpression,
    mappers: dict[Table, Mapper],
    intermediate_result: dict[Mapper, ReferencedEntity],
    parameters: dict[str, Any],
) -> None:
    left = condition.left
    right = condition.right

    if isinstance(left, ColumnClause) and isinstance(right, BindParameter):
        table = left.table
        primary_key_columns = table.primary_key.columns.values()
        if left in primary_key_columns:
            if isinstance(table, Table) and (mapper := mappers.get(table)):
                ref_entity = intermediate_result[mapper]
                key_name = left.name
                key_value = right.effective_value or parameters.get(right.key)
                if key_value is not None:
                    ref_entity.keys[key_name] = key_value


def _traverse_conditions(
    condition: BooleanClauseList | BinaryExpression | None,
    mappers: dict[Table, Mapper],
    intermediate_result: dict[Mapper, ReferencedEntity],
    parameters: dict[str, Any],
) -> None:
    if condition is not None:
        if hasattr(condition, "clauses"):
            for child in condition.clauses:
                _traverse_conditions(child, mappers, intermediate_result, parameters)
        else:
            _process_condition(condition, mappers, intermediate_result, parameters)


def _collect_entities(state: ORMExecuteState) -> list[ReferencedEntity]:
    intermediate_result = {}

    if not isinstance(state.statement, Select):
        return []
    select_statement = state.statement

    # Extract mappers from the FROM clause
    tables = select_statement.get_final_froms()
    mappers = {mapper.local_table: mapper for mapper in state.all_mappers}

    for table in tables:
        if mapper := mappers.get(table):
            intermediate_result[mapper] = ReferencedEntity(entity=mapper, keys={})

    # Extract primary key conditions from the WHERE clause, if any
    where_clause = select_statement.whereclause
    _traverse_conditions(where_clause, mappers, intermediate_result, state.parameters or {})

    return list(intermediate_result.values())