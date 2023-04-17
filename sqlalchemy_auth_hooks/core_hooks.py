import asyncio
from collections import defaultdict
from functools import partial
from threading import Thread
from typing import Any

from sqlalchemy import (
    ClauseElement,
    Connection,
    Engine,
    ResultProxy,
    Select,
    Update,
    event,
    inspect,
    Column,
    BindParameter,
)
from sqlalchemy.orm import DeclarativeMeta, Session

from sqlalchemy_auth_hooks.common_hooks import _Hook
from sqlalchemy_auth_hooks.handler import ReferencedEntity, SQLAlchemyAuthHandler
from sqlalchemy_auth_hooks.utils import _traverse_conditions, run_loop


class CoreHooks:
    def __init__(self, handler: SQLAlchemyAuthHandler) -> None:
        self.handler = handler
        self._tasks: set[asyncio.Task] = set()
        self._pending_hooks: dict[Session, dict[tuple[Any] | None, list[_Hook]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._loop = asyncio.new_event_loop()
        self._executor_thread = Thread(target=partial(run_loop, self._loop), daemon=True)
        self._executor_thread.start()

    def before_execute(
        self,
        conn: Connection,
        clauseelement: ClauseElement,
        multiparams: list[Any],
        params: dict[Any, Any],
        execution_options: dict[str, Any],
    ) -> None:
        return
        if isinstance(clauseelement, Select):
            entities = _collect_entities(clauseelement)
            handler.on_select(entities)

    def after_execute(
        self,
        conn: Connection,
        clauseelement: ClauseElement,
        multiparams: list[Any],
        params: dict[Any, Any],
        execution_options: dict[str, Any],
        result: ResultProxy,
    ) -> None:
        if isinstance(clauseelement, Update):
            if "entity" not in clauseelement.entity_description:
                # ORM update
                return
            entity_cls: DeclarativeMeta = clauseelement.entity_description["entity"]
            registry = entity_cls.registry
            table_mappers = {mapper.local_table: mapper for mapper in registry.mappers}
            mapper = table_mappers[clauseelement.entity_description["table"]]

            references = {
                mapper: {
                    clauseelement.entity_description["table"]: ReferencedEntity(
                        entity=mapper,
                        selectable=clauseelement.entity_description["table"],
                    )
                }
            }
            _traverse_conditions(clauseelement.whereclause, table_mappers, references, {})

            updated_data = {}
            col: Column
            parameter: BindParameter
            for col, parameter in clauseelement._values.items():
                updated_data[col.name] = parameter.value

            for mapped_dict in references.values():
                for referenced_entity in mapped_dict.values():
                    self.handler.on_update(referenced_entity, updated_data)


def _register_core_hooks(handler: SQLAlchemyAuthHandler) -> None:
    """
    Register hooks for SQLAlchemy Core events.
    """

    hooks = CoreHooks(handler)
    event.listen(Engine, "before_execute", hooks.before_execute)
    event.listen(Engine, "after_execute", hooks.after_execute)
