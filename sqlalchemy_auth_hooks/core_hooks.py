import asyncio
from functools import partial
from threading import Thread
from typing import Any, Callable, Coroutine, TypeVar, cast

from sqlalchemy import (
    BindParameter,
    ClauseElement,
    Column,
    Connection,
    Engine,
    FromClause,
    ResultProxy,
    Table,
    Update,
    event,
)
from sqlalchemy.orm import DeclarativeMeta, Mapper

from sqlalchemy_auth_hooks.handler import ReferencedEntity, SQLAlchemyAuthHandler
from sqlalchemy_auth_hooks.utils import run_loop, traverse_conditions

T = TypeVar("T")


class CoreHooks:
    def __init__(self, handler: SQLAlchemyAuthHandler) -> None:
        self.handler = handler
        self._loop = asyncio.new_event_loop()
        self._executor_thread = Thread(target=partial(run_loop, self._loop), daemon=True)
        self._executor_thread.start()

    def call_async(self, func: Callable[..., Coroutine[T, None, Any]], *args: Any) -> T:
        future = asyncio.run_coroutine_threadsafe(func(*args), self._loop)
        return future.result()

    def before_execute(
        self,
        conn: Connection,
        clauseelement: ClauseElement,
        multiparams: list[Any],
        params: dict[Any, Any],
        execution_options: dict[str, Any],
    ) -> None:
        return
        # if isinstance(clauseelement, Select):
        #     entities = _collect_entities(clauseelement)
        #     handler.before_select(entities)

    def after_execute(
        self,
        conn: Connection,
        clauseelement: ClauseElement,
        multiparams: list[Any],
        params: dict[Any, Any],
        execution_options: dict[str, Any],
        result: ResultProxy[Any],
    ) -> None:
        if isinstance(clauseelement, Update):
            self.handle_update(clauseelement)

    def handle_update(self, clause_element: Update) -> None:
        if "entity" not in clause_element.entity_description:
            # ORM update
            return
        entity_cls: DeclarativeMeta = clause_element.entity_description["entity"]
        registry = entity_cls.registry
        table_mappers: dict[FromClause, Mapper[Any]] = {mapper.local_table: mapper for mapper in registry.mappers}
        mapper = table_mappers[clause_element.entity_description["table"]]

        references: dict[Mapper[Any], dict[Table, ReferencedEntity]] = {
            mapper: {
                clause_element.entity_description["table"]: ReferencedEntity(
                    entity=mapper,
                    selectable=clause_element.entity_description["table"],
                )
            }
        }
        conditions = traverse_conditions(clause_element.whereclause, {})

        parameters = cast(dict[Column[Any], BindParameter[Any]], clause_element._values)  # type: ignore
        updated_data: dict[str, Any] = {col.name: parameter.value for col, parameter in parameters.items()}
        for mapped_dict in references.values():
            for referenced_entity in mapped_dict.values():
                self.call_async(self.handler.after_core_update, referenced_entity, conditions, updated_data)


def register_core_hooks(handler: SQLAlchemyAuthHandler) -> None:
    """
    Register hooks for SQLAlchemy Core events.
    """

    hooks = CoreHooks(handler)
    event.listen(Engine, "before_execute", hooks.before_execute)
    event.listen(Engine, "after_execute", hooks.after_execute)
