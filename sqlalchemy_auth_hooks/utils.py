import asyncio
from collections import defaultdict
from typing import Any, Generator, Mapping, Sequence, cast

import structlog
from sqlalchemy import (
    BindParameter,
    ColumnClause,
    FromClause,
    Join,
    Select,
    Table,
)
from sqlalchemy.orm import Mapper, ORMExecuteState
from sqlalchemy.sql.elements import ColumnElement, ExpressionClauseList, UnaryExpression
from sqlalchemy.sql.operators import and_, eq, ne
from sqlalchemy.sql.selectable import Alias, ReturnsRows

from sqlalchemy_auth_hooks.references import (
    CompositeConditions,
    EntityConditions,
    ReferenceConditions,
    ReferencedEntity,
)

logger = structlog.get_logger()


def run_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def get_parameter_value(
    parameter: BindParameter[Any], parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None
) -> Any | None:
    effective_value = parameter.effective_value
    if isinstance(parameters, dict):
        return parameters.get(parameter.key, effective_value)
    elif isinstance(parameters, list):
        return next(
            (param[parameter.key] for param in parameters if parameter.key in param),
            effective_value,
        )
    else:
        return effective_value


def _process_condition(
    condition: ColumnElement[Any],
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
) -> ReferenceConditions | None:
    if isinstance(condition, UnaryExpression):
        return

    if isinstance(condition.left, ColumnClause):
        left: ColumnClause[Any] = condition.left
        right = condition.right
    elif isinstance(condition.right, ColumnClause) and condition.operator in (eq, ne):
        left: ColumnClause[Any] = condition.right
        right = condition.left
    else:
        # We only care about conditions that involve columns
        return None

    selectable = left.table
    if selectable is None:
        return None

    table = selectable.element if isinstance(selectable, Alias) else selectable

    if isinstance(table, Table):
        if isinstance(right, BindParameter):
            parameter = cast(BindParameter[Any], right)
            key_value = get_parameter_value(parameter, parameters)
            key_name = left.name
            return ReferenceConditions(
                selectable=selectable,
                conditions={key_name: {"operator": condition.operator, "value": key_value}},
            )
        else:
            # Both are columns, not interesting
            return


def traverse_conditions(
    condition: ColumnElement[Any] | None,
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
) -> EntityConditions | None:
    if condition is None:
        return None

    if not isinstance(condition, ExpressionClauseList):
        return _process_condition(condition, parameters)
    conditions = CompositeConditions(conditions=[], operator=condition.operator)
    for child in condition.clauses:
        if child_condition := traverse_conditions(child, parameters):
            conditions.conditions.append(child_condition)
    return conditions


def _extract_mappers_from_clause(
    clause: FromClause, table_mappers: dict[FromClause, Mapper[Any]]
) -> Generator[tuple[Mapper[Any], ReturnsRows], None, None]:
    if isinstance(clause, Table):
        if mapper := table_mappers.get(clause):
            yield mapper, clause.selectable
    elif isinstance(clause, Join):
        yield from _extract_mappers_from_clause(clause.left, table_mappers)
        yield from _extract_mappers_from_clause(clause.right, table_mappers)
    elif isinstance(clause, Alias):
        yield next(_extract_mappers_from_clause(clause.element, table_mappers))[0], clause.selectable


def process_clauses(
    froms: Sequence[FromClause],
    intermediate_result: dict[Mapper[Any], dict[ReturnsRows, ReferencedEntity]],
    where_clause: Any,
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    table_mappers: dict[FromClause, Mapper[Any]],
) -> tuple[dict[Mapper[Any], dict[ReturnsRows, ReferencedEntity]], EntityConditions | None]:
    all_conditions: list[EntityConditions] = []
    for from_clause in froms:
        if isinstance(from_clause, Join) and isinstance(from_clause.onclause, ExpressionClauseList):
            for clause in from_clause.onclause.clauses:
                condition = traverse_conditions(clause, parameters)
                if condition is not None:
                    all_conditions.append(condition)

        for mapper, selectable in _extract_mappers_from_clause(from_clause, table_mappers):
            intermediate_result[mapper][selectable] = ReferencedEntity(entity=mapper, selectable=selectable)

    # Extract primary key conditions from the WHERE clause, if any
    where_conditions = traverse_conditions(where_clause, parameters)

    if where_conditions is not None:
        all_conditions.append(where_conditions)

    if len(all_conditions) == 1:
        conditions = all_conditions[0]
    elif not all_conditions:
        conditions = None
    else:
        conditions = CompositeConditions(conditions=all_conditions, operator=and_)

    return intermediate_result, conditions


def collect_entities(state: ORMExecuteState) -> tuple[list[ReferencedEntity], EntityConditions | None]:
    intermediate_result: dict[Mapper[Any], dict[ReturnsRows, ReferencedEntity]] = defaultdict(dict)

    if not isinstance(state.statement, Select):
        return [], None
    select_statement: Select[Any] = state.statement

    # Extract mappers from the FROM clause
    if state.bind_mapper is None:
        logger.warning("No bind mapper found for %s", state.statement)
        return [], None
    registry = state.bind_mapper.registry
    froms = select_statement.get_final_froms()
    table_mappers = {mapper.local_table: mapper for mapper in registry.mappers}

    results, conditions = process_clauses(
        froms,
        intermediate_result,
        select_statement.whereclause,
        state.parameters or {},
        table_mappers,
    )

    return [entity for mapper_ref in results.values() for entity in mapper_ref.values()], conditions
