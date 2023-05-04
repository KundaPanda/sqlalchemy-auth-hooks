import asyncio
from typing import Any, cast

import structlog
from sqlalchemy import (
    FromClause,
    Insert,
)
from sqlalchemy.orm import DeclarativeBase, Mapper

logger = structlog.get_logger()


def run_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def get_table_mapper(entity: DeclarativeBase) -> Mapper[Any]:
    registry = entity.registry
    table_mappers: dict[FromClause, Mapper[Any]] = {mapper.local_table: mapper for mapper in registry.mappers}
    return table_mappers[entity.__table__]


def get_insert_columns(statement: Insert) -> list[dict[str, Any]]:
    if statement._values:  # type: ignore
        return [{c.name: v.effective_value for c, v in statement._values.items()}]  # type: ignore

    results: list[dict[str, Any]] = []
    for tuple_ in statement._multi_values:  # type: ignore
        results.extend({cast(str, c.name): v for c, v in entry.items()} for entry in tuple_)  # type: ignore
    return results
