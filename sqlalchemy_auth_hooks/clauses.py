from collections import defaultdict
from typing import Any, Generator, Mapping, Sequence

import structlog
from sqlalchemy import (
    Delete,
    FromClause,
    Join,
    Select,
    Table,
    Update,
)
from sqlalchemy.orm import Mapper, ORMExecuteState
from sqlalchemy.sql.elements import ColumnElement, ExpressionClauseList
from sqlalchemy.sql.operators import and_
from sqlalchemy.sql.selectable import Alias, ReturnsRows

from sqlalchemy_auth_hooks.conditions import traverse_conditions
from sqlalchemy_auth_hooks.references import (
    CompositeCondition,
    EntityCondition,
    ReferencedEntity,
)
from sqlalchemy_auth_hooks.utils import get_table_mapper

logger = structlog.get_logger()


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


def _process_join_clause(
    from_clause: Join, parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None
) -> list[EntityCondition]:
    all_conditions: list[EntityCondition] = []
    if isinstance(from_clause.onclause, ExpressionClauseList):
        for clause in from_clause.onclause.clauses:
            condition = traverse_conditions(clause, parameters)
            if condition is not None:
                all_conditions.append(condition)
    elif isinstance(from_clause.onclause, ColumnElement):
        condition = traverse_conditions(from_clause.onclause, parameters)
        if condition is not None:
            all_conditions.append(condition)
    return all_conditions


def process_clauses(
    froms: Sequence[FromClause],
    intermediate_result: dict[Mapper[Any], dict[ReturnsRows, ReferencedEntity]],
    where_clause: Any,
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    table_mappers: dict[FromClause, Mapper[Any]],
) -> tuple[dict[Mapper[Any], dict[ReturnsRows, ReferencedEntity]], EntityCondition | None]:
    all_conditions: list[EntityCondition] = []
    for from_clause in froms:
        if isinstance(from_clause, Join):
            all_conditions.extend(_process_join_clause(from_clause, parameters))

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
        conditions = CompositeCondition(conditions=all_conditions, operator=and_)

    return intermediate_result, conditions


def collect_entities(state: ORMExecuteState) -> tuple[list[ReferencedEntity], EntityCondition | None]:
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


def extract_references(
    statement: Update | Delete,
) -> tuple[EntityCondition | None, dict[Mapper[Any], dict[Table, ReferencedEntity]]]:
    mapper = get_table_mapper(statement.entity_description["entity"])
    references: dict[Mapper[Any], dict[Table, ReferencedEntity]] = {
        mapper: {
            statement.entity_description["table"]: ReferencedEntity(
                entity=mapper,
                selectable=statement.entity_description["table"],
            )
        }
    }
    conditions = traverse_conditions(statement.whereclause, {})
    return conditions, references
