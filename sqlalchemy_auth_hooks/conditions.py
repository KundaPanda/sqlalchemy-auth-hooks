from typing import Any, Mapping, Sequence

import structlog
from sqlalchemy import (
    BindParameter,
    ColumnClause,
    true,
)
from sqlalchemy.sql.elements import BinaryExpression, ColumnElement, ExpressionClauseList, UnaryExpression
from sqlalchemy.sql.operators import is_true

from sqlalchemy_auth_hooks.references import (
    ColumnExpression,
    CompositeCondition,
    EntityCondition,
    Expression,
    LiteralExpression,
    NestedExpression,
    ReferenceCondition,
    UnaryCondition,
)

logger = structlog.get_logger()


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
        if isinstance(left, (ColumnClause, LiteralExpression)) and isinstance(right, (ColumnClause, LiteralExpression)):
            return ColumnExpression(operator=expr.operator, left=left, right=right)
        return NestedExpression(operator=expr.operator, left=left, right=right)

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
