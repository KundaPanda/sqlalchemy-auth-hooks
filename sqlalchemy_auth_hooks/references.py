import abc
from typing import Any

from sqlalchemy import ColumnClause, ReturnsRows
from sqlalchemy.orm import Mapper
from sqlalchemy.sql.operators import OperatorType


class ReferencedEntity:
    def __init__(
        self,
        entity: Mapper[Any],
        selectable: ReturnsRows,
    ) -> None:
        self.entity = entity
        self.selectable = selectable

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReferencedEntity):
            raise NotImplementedError(f"Cannot compare {self} with {other}")
        return self.entity == other.entity and self.selectable == other.selectable

    def __repr__(self) -> str:
        return f"ReferencedEntity(entity={self.entity}, selectable={repr(self.selectable)})"  # pragma: no cover


class EntityCondition:
    def __init__(self, operator: OperatorType) -> None:
        self.operator = operator


class UnaryCondition(EntityCondition):
    def __init__(self, operator: OperatorType, value: Any) -> None:
        super().__init__(operator)
        self.value = value

    def __eq__(self, other: object) -> bool:
        return (
            self.operator == other.operator and self.value == other.value
            if isinstance(other, UnaryCondition)
            else False
        )

    def __repr__(self) -> str:
        return f"UnaryCondition(operator={self.operator.__name__}, value={self.value})"


class CompositeCondition(EntityCondition):
    def __init__(self, operator: OperatorType, conditions: list[EntityCondition]) -> None:
        super().__init__(operator)
        self.conditions = conditions

    def __eq__(self, other: object) -> bool:
        return (
            self.conditions == other.conditions and self.operator == other.operator
            if isinstance(other, CompositeCondition)
            else False
        )

    def __repr__(self) -> str:
        return (
            f"CompositeCondition(operator={self.operator.__name__}, conditions={self.conditions})"  # pragma: no cover
        )


class Expression(abc.ABC):
    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        ...


class LiteralExpression(Expression):
    def __init__(self, value: Any) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        return self.value == other.value if isinstance(other, LiteralExpression) else False

    def __repr__(self) -> str:
        return f"LiteralExpression(value={self.value})"


class ColumnExpression(Expression):
    def __init__(
        self,
        left: ColumnClause[Any] | LiteralExpression,
        operator: OperatorType,
        right: ColumnClause[Any] | LiteralExpression,
    ) -> None:
        self.left = left
        self.operator = operator
        self.right = right

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ColumnExpression)
            and _cmp_expressions(self.left, other.left)
            and _cmp_expressions(self.right, other.right)
            and self.operator == other.operator
        )

    def __repr__(self) -> str:
        return f"Expression(left={self.left}, operator={self.operator.__name__}, right={self.right})"


class NestedExpression(Expression):
    def __init__(
        self, left: Expression | ColumnClause[Any], operator: OperatorType, right: Expression | ColumnClause[Any]
    ) -> None:
        self.left = left
        self.operator = operator
        self.right = right

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, NestedExpression)
            and _cmp_expressions(self.left, other.left)
            and _cmp_expressions(self.right, other.right)
            and self.operator == other.operator
        )

    def __repr__(self) -> str:
        return f"NestedExpression(left={self.left}, operator={self.operator.__name__}, right={self.right})"


class ReferenceCondition(EntityCondition):
    def __init__(
        self, left: Expression | ColumnClause[Any], operator: OperatorType, right: Expression | ColumnClause[Any]
    ) -> None:
        super().__init__(operator)
        self.left = left
        self.right = right

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ReferenceCondition)
            and _cmp_expressions(self.left, other.left)
            and _cmp_expressions(self.right, other.right)
            and self.operator == other.operator
        )

    def __repr__(self) -> str:
        return f"ReferenceCondition(left={self.left}, operator={self.operator.__name__}, right={self.right})"


def _cmp_expressions(left: Expression | ColumnClause[Any], right: Expression | ColumnClause[Any]) -> bool:
    if not isinstance(left, ColumnClause):
        return left == right
    return left.compare(right) if isinstance(right, ColumnClause) else False
