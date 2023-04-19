from typing import Any

from sqlalchemy import Alias, FromClause, ReturnsRows
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
        return f"ReferencedEntity({self.entity}, {repr(self.selectable)})"  # pragma: no cover


class EntityConditions:
    pass


class CompositeConditions(EntityConditions):
    def __init__(self, operator: OperatorType, conditions: list[EntityConditions]) -> None:
        self.conditions = conditions
        self.operator = operator

    def __eq__(self, other: object) -> bool:
        return (
            self.conditions == other.conditions and self.operator == other.operator
            if isinstance(other, CompositeConditions)
            else False
        )

    def __repr__(self) -> str:
        return f"ConditionsClause({self.operator}[{self.conditions}])"  # pragma: no cover


class ReferenceConditions(EntityConditions):
    def __init__(self, selectable: Alias | FromClause, conditions: dict[str, Any]) -> None:
        self.selectable = selectable
        self.conditions = conditions

    def __eq__(self, other: object) -> bool:
        return (
            self.selectable == other.selectable and self.conditions == other.conditions
            if isinstance(other, ReferenceConditions)
            else False
        )

    def __repr__(self) -> str:
        return f"ReferenceConditions({self.selectable}, {self.conditions})"  # pragma: no cover
