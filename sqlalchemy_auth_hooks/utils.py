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
from sqlalchemy.sql.elements import ExpressionClauseList
from sqlalchemy.sql.operators import and_, eq, ne
from sqlalchemy.sql.selectable import Alias

from sqlalchemy_auth_hooks.references import (
    CompositeConditions,
    EntityConditions,
    ReferenceConditions,
    ReferencedEntity,
)


def run_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def _process_condition(
    condition: BinaryExpression,
    parameters: dict[str, Any],
) -> ReferenceConditions | None:
    left = condition.left
    right = condition.right
    if not isinstance(left, ColumnClause):
        if isinstance(right, ColumnClause) and condition.operator in (eq, ne):
            left, right = right, left
        else:
            # We only care about conditions that involve columns
            return None

    selectable = left.table
    if isinstance(selectable, Alias):
        table = cast(Table, selectable.element)
    else:
        table = cast(Table, selectable)
    if isinstance(table, Table):
        if isinstance(right, BindParameter):
            key_value = right.effective_value or parameters.get(right.key)
            key_name = left.name
            return ReferenceConditions(
                selectable=selectable,
                conditions={key_name: {"operator": condition.operator, "value": key_value}},
            )
        else:
            # Both are columns, not interesting
            return


def _traverse_conditions(
    condition: BooleanClauseList | BinaryExpression | None,
    parameters: dict[str, Any],
) -> EntityConditions | None:
    if condition is None:
        return None

    if not isinstance(condition, ExpressionClauseList):
        return _process_condition(condition, parameters)
    conditions = CompositeConditions(conditions=[], operator=condition.operator)
    for child in condition.clauses:
        conditions.conditions.append(_traverse_conditions(child, parameters))
    return conditions


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


def _collect_entities(state: ORMExecuteState) -> tuple[list[ReferencedEntity], EntityConditions | None]:
    intermediate_result: dict[Mapper, dict[FromClause, ReferencedEntity]] = defaultdict(dict)

    if not isinstance(state.statement, Select):
        return [], None
    select_statement = state.statement

    # Extract mappers from the FROM clause
    registry = state.bind_mapper.registry
    froms = select_statement.get_final_froms()
    table_mappers = {mapper.local_table: mapper for mapper in registry.mappers}

    all_conditions = []
    for from_clause in froms:
        if isinstance(from_clause, Join) and isinstance(from_clause.onclause, ExpressionClauseList):
            for clause in from_clause.onclause.clauses:
                condition = _traverse_conditions(clause, state.parameters or {})
                if condition is not None:
                    all_conditions.append(condition)

        for mapper, selectable in _extract_mappers_from_clause(from_clause, table_mappers):
            intermediate_result[mapper][selectable] = ReferencedEntity(entity=mapper, selectable=selectable)

    # Extract primary key conditions from the WHERE clause, if any
    where_clause = select_statement.whereclause
    where_conditions = _traverse_conditions(where_clause, state.parameters or {})

    if where_conditions is not None:
        all_conditions.append(where_conditions)

    if len(all_conditions) == 1:
        conditions = all_conditions[0]
    elif not all_conditions:
        conditions = None
    else:
        conditions = CompositeConditions(conditions=all_conditions, operator=and_)

    return [entity for mapper in intermediate_result for entity in intermediate_result[mapper].values()], conditions
