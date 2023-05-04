# pyright: reportUnnecessaryIsInstance=false

import asyncio
from collections import defaultdict
from typing import Any, Generator, Mapping, Sequence, cast

import structlog
from sqlalchemy import (
    BindParameter,
    ColumnClause,
    Delete,
    FromClause,
    Insert,
    Join,
    Select,
    Table,
    Update,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapper, ORMExecuteState
from sqlalchemy.sql.elements import BinaryExpression, ColumnElement, ExpressionClauseList, UnaryExpression
from sqlalchemy.sql.operators import and_, is_true
from sqlalchemy.sql.selectable import Alias, ReturnsRows

from sqlalchemy_auth_hooks.references import (
    ColumnExpression,
    CompositeCondition,
    EntityCondition,
    Expression,
    LiteralExpression,
    NestedExpression,
    ReferenceCondition,
    ReferencedEntity,
    UnaryCondition,
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


def _process_expr(
    expr: ColumnElement[Any] | BindParameter[Any],
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
) -> ColumnClause[Any] | Expression:
    if isinstance(expr, BindParameter):
        return LiteralExpression(get_parameter_value(expr, parameters))

    if isinstance(expr, BinaryExpression):
        left = _process_expr(expr.left, parameters)
        right = _process_expr(expr.right, parameters)
        if isinstance(left, Expression) or isinstance(right, Expression):
            return NestedExpression(operator=expr.operator, left=left, right=right)
        if isinstance(left, ColumnClause):
            return ColumnExpression(operator=expr.operator, left=left, right=right)
        if isinstance(right, ColumnClause):
            return ColumnExpression(operator=expr.operator, left=left, right=right)
        logger.warning("Could not process expression", expr=expr, left=left, right=right)
        return LiteralExpression(None)

    if isinstance(expr, ColumnClause):
        return expr

    logger.warning("Could not process expression", expr=expr)
    return LiteralExpression(None)


def _process_condition(
    condition: ColumnElement[Any],
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
) -> EntityCondition | None:
    if isinstance(condition, UnaryExpression):
        if condition.operator == is_true and condition.element == true():
            # Ignore 1 = 1 conditions
            return None
        if condition.operator is None:
            # Ignore is null conditions
            logger.warning("Ignoring condition", condition=condition)
            return None
        return UnaryCondition(operator=condition.operator, value=condition.element)

    left_expr = _process_expr(condition.left, parameters)
    right_expr = _process_expr(condition.right, parameters)
    return ReferenceCondition(
        left=left_expr,
        operator=condition.operator,
        right=right_expr,
    )


def traverse_conditions(
    condition: ColumnElement[Any] | None,
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
) -> EntityCondition | None:
    if condition is None:
        return None

    if not isinstance(condition, ExpressionClauseList):
        return _process_condition(condition, parameters)
    conditions = CompositeCondition(conditions=[], operator=condition.operator)
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


def get_table_mapper(entity: DeclarativeBase) -> Mapper[Any]:
    registry = entity.registry
    table_mappers: dict[FromClause, Mapper[Any]] = {mapper.local_table: mapper for mapper in registry.mappers}
    return table_mappers[entity.__table__]


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


def get_insert_columns(statement: Insert) -> list[dict[str, Any]]:
    if statement._values:  # type: ignore
        return [{c.name: v.effective_value for c, v in statement._values.items()}]  # type: ignore

    results: list[dict[str, Any]] = []
    for tuple_ in statement._multi_values:  # type: ignore
        results.extend({cast(str, c.name): v for c, v in entry.items()} for entry in tuple_)  # type: ignore
    return results
