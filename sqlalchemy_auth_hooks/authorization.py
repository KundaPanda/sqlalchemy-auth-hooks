from typing import Any, Iterable, cast

from sqlalchemy import (
    BindParameter,
    Column,
    Delete,
    Insert,
    Update,
    true,
)
from sqlalchemy.orm import (
    InstanceState,
    Mapper,
    ORMExecuteState,
    with_loader_criteria,
)
from sqlalchemy.sql.operators import eq

from sqlalchemy_auth_hooks.auth_handler import AuthHandler
from sqlalchemy_auth_hooks.references import ReferenceConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession
from sqlalchemy_auth_hooks.utils import collect_entities, extract_references, get_insert_columns, get_table_mapper


class StatementAuthorizer:
    def __init__(self, auth_handler: AuthHandler) -> None:
        self.auth_handler = auth_handler

    async def authorize_update(self, orm_execute_state: ORMExecuteState) -> None:
        statement = cast(Update, orm_execute_state.statement)
        conditions, references = extract_references(statement)

        for refs in references.values():
            parameters = cast(dict[Column[Any], BindParameter[Any]], statement._values)  # type: ignore
            async for selectable, filter_exp in self.auth_handler.before_update(
                cast(AuthorizedSession, orm_execute_state.session),
                list(refs.values()),
                conditions,
                {c.name: v.effective_value for c, v in parameters.items()},
            ):
                where_clause = with_loader_criteria(selectable, filter_exp, include_aliases=True)
                orm_execute_state.statement = orm_execute_state.statement.options(where_clause)

    async def authorize_insert(self, orm_execute_state: ORMExecuteState) -> None:
        statement = cast(Insert, orm_execute_state.statement)
        entity = ReferencedEntity(
            entity=get_table_mapper(statement.entity_description["entity"]), selectable=statement.table
        )
        columns = get_insert_columns(statement)
        async for selectable, filter_exp in self.auth_handler.before_insert(
            cast(AuthorizedSession, orm_execute_state.session),
            entity,
            columns,
        ):
            where_clause = with_loader_criteria(selectable, filter_exp, include_aliases=True)
            orm_execute_state.statement = orm_execute_state.statement.options(where_clause)

    async def authorize_delete(self, orm_execute_state: ORMExecuteState) -> None:
        statement = cast(Delete, orm_execute_state.statement)
        conditions, references = extract_references(statement)

        for refs in references.values():
            async for selectable, filter_exp in self.auth_handler.before_delete(
                cast(AuthorizedSession, orm_execute_state.session),
                list(refs.values()),
                conditions,
            ):
                where_clause = with_loader_criteria(selectable, filter_exp, include_aliases=True)
                orm_execute_state.statement = orm_execute_state.statement.options(where_clause)

    async def authorize_object_insert(self, session: AuthorizedSession, states: Iterable[InstanceState[Any]]) -> None:
        for state in states:
            mapper: Mapper[Any] = state.mapper  # type: ignore
            async for _, filter_exp in self.auth_handler.before_insert(
                session,
                ReferencedEntity(mapper, state.class_.__table__),
                [{k: v for k, v in state.dict.items() if k in mapper.columns}],
            ):
                if filter_exp != true():
                    session.rollback()
                    return

    async def authorize_object_delete(self, session: AuthorizedSession, states: Iterable[InstanceState[Any]]) -> None:
        for state in states:
            mapper: Mapper[Any] = state.mapper  # type: ignore
            async for _, filter_exp in self.auth_handler.before_delete(
                session,
                [ReferencedEntity(mapper, state.class_.__table__)],
                ReferenceConditions(
                    selectable=state.class_.__table__,
                    conditions={
                        key.name: {"operator": eq, "value": state.dict[key.name]} for key in mapper.primary_key
                    },
                ),
            ):
                if filter_exp != true():
                    session.rollback()
                    return

    async def authorize_object_update(
        self, session: AuthorizedSession, states: Iterable[tuple[InstanceState[Any], dict[str, Any]]]
    ) -> None:
        for state, changes in states:
            mapper: Mapper[Any] = state.mapper  # type: ignore
            async for _, filter_exp in self.auth_handler.before_update(
                session,
                [ReferencedEntity(mapper, state.class_.__table__)],
                ReferenceConditions(
                    selectable=state.class_.__table__,
                    conditions={
                        key.name: {"operator": eq, "value": state.dict[key.name]} for key in mapper.primary_key
                    },
                ),
                changes,
            ):
                if filter_exp != true():
                    session.rollback()
                    return

    async def authorize_select(self, orm_execute_state: ORMExecuteState) -> None:
        entities, conditions = collect_entities(orm_execute_state)

        async for selectable, filter_exp in self.auth_handler.before_select(
            cast(AuthorizedSession, orm_execute_state.session), entities, conditions
        ):
            where_clause = with_loader_criteria(selectable, filter_exp, include_aliases=True)
            orm_execute_state.statement = orm_execute_state.statement.options(where_clause)
