import asyncio
from collections import defaultdict
from typing import Any, Generator, cast

from sqlalchemy import (
    BinaryExpression,
    BindParameter,
    BooleanClauseList,
    ColumnClause,
    FromClause,
    Join,
    Select,
    Table,
)
from sqlalchemy.orm import Mapper, ORMExecuteState
from sqlalchemy.sql import operators
from sqlalchemy.sql.selectable import Alias

from sqlalchemy_auth_hooks.handler import ReferencedEntity


def run_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def _process_condition(
    condition: BinaryExpression,
    mappers: dict[Table, Mapper],
    intermediate_result: dict[Mapper, dict[FromClause, ReferencedEntity]],
    parameters: dict[str, Any],
) -> None:
    if condition.operator != operators.eq:
        # We only care about equality conditions for now
        return
    left = condition.left
    right = condition.right

    if isinstance(left, ColumnClause) and isinstance(right, BindParameter):
        selectable = left.table
        if isinstance(selectable, Alias):
            table = cast(Table, selectable.element)
        else:
            table = cast(Table, selectable)
        primary_key_columns = table.primary_key.columns.values()
        if any(pk.key == left.key for pk in primary_key_columns):
            if isinstance(table, Table) and (mapper := mappers.get(table)):
                ref_entity = intermediate_result[mapper][selectable]
                key_name = left.name
                key_value = right.effective_value or parameters.get(right.key)
                if key_value is not None:
                    ref_entity.keys[key_name] = key_value


def _traverse_conditions(
    condition: BooleanClauseList | BinaryExpression | None,
    mappers: dict[Table, Mapper],
    intermediate_result: dict[Mapper, dict[FromClause, ReferencedEntity]],
    parameters: dict[str, Any],
) -> None:
    if condition is not None:
        if hasattr(condition, "clauses"):
            for child in condition.clauses:
                _traverse_conditions(child, mappers, intermediate_result, parameters)
        else:
            _process_condition(condition, mappers, intermediate_result, parameters)


def _extract_mappers_from_clause(
    clause: FromClause, table_mappers: dict[Table, Mapper]
) -> Generator[tuple[Mapper, FromClause], None, None]:
    if isinstance(clause, Table):
        if mapper := table_mappers.get(clause):
            yield mapper, clause.selectable
    elif isinstance(clause, Join):
        yield from _extract_mappers_from_clause(clause.left, table_mappers)
        yield from _extract_mappers_from_clause(clause.right, table_mappers)
    elif isinstance(clause, Alias):
        yield next(_extract_mappers_from_clause(clause.element, table_mappers))[0], clause.selectable


def _collect_entities(state: ORMExecuteState) -> list[ReferencedEntity]:
    intermediate_result: dict[Mapper, dict[FromClause, ReferencedEntity]] = defaultdict(dict)

    if not isinstance(state.statement, Select):
        return []
    select_statement = state.statement

    # Extract mappers from the FROM clause
    registry = state.bind_mapper.registry
    froms = select_statement.get_final_froms()
    table_mappers = {mapper.local_table: mapper for mapper in registry.mappers}

    for from_clause in froms:
        for mapper, selectable in _extract_mappers_from_clause(from_clause, table_mappers):
            intermediate_result[mapper][selectable] = ReferencedEntity(entity=mapper, selectable=selectable, keys={})

    # Extract primary key conditions from the WHERE clause, if any
    where_clause = select_statement.whereclause
    _traverse_conditions(where_clause, table_mappers, intermediate_result, state.parameters or {})

    return [entity for mapper in intermediate_result for entity in intermediate_result[mapper].values()]
