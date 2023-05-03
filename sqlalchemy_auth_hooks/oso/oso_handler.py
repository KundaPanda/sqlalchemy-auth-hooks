from typing import Any, AsyncIterator, TypedDict, cast

import structlog
from oso import Oso
from sqlalchemy import false, inspect
from sqlalchemy.orm import Mapper
from sqlalchemy.sql.roles import ExpressionElementRole

from sqlalchemy_auth_hooks.auth_handler import AuthHandler
from sqlalchemy_auth_hooks.oso.sqlalchemy_oso.auth import authorize_model
from sqlalchemy_auth_hooks.post_auth_handler import PostAuthHandler
from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession

logger = structlog.get_logger()


class CheckedPermissions(TypedDict):
    insert: str | None
    delete: str | None
    update: str | None
    select: str | None


class OsoAuthHandler(AuthHandler):
    def __init__(
        self,
        oso: Oso,
        checked_permissions: dict[type[Any], CheckedPermissions],
        default_checked_permission: str | None = None,
    ) -> None:
        self.oso = oso
        self.checked_permissions: dict[Mapper[Any], CheckedPermissions] = {
            cast(Mapper[Any], inspect(entity)).mapper: permission for entity, permission in checked_permissions.items()
        }
        self.default_checked_permissions: CheckedPermissions = {
            "insert": default_checked_permission,
            "delete": default_checked_permission,
            "update": default_checked_permission,
            "select": default_checked_permission,
        }

    async def authorize_action(
        self, referenced_entity: Mapper[Any], session: AuthorizedSession, permission: str
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        checked_permission = self.checked_permissions.get(referenced_entity, self.default_checked_permissions).get(
            permission
        )
        if checked_permission is None:
            logger.warning(f"No permission to check for {referenced_entity}")
            yield referenced_entity, false()
            return
        filter_ = authorize_model(self.oso, session.user, checked_permission, session, referenced_entity.class_)
        if filter_ is not None:
            logger.debug("Filtering %s with %s", referenced_entity, filter_)
            yield referenced_entity, filter_
        else:
            logger.warning("No filter for %s", referenced_entity)

    async def before_insert(
        self, session: AuthorizedSession, entity: ReferencedEntity, values: list[dict[str, Any]]
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        async for rule in self.authorize_action(entity.entity, session, "insert"):
            yield rule

    async def before_delete(
        self,
        session: AuthorizedSession,
        referenced_entities: list[ReferencedEntity],
        conditions: EntityConditions | None,
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        for referenced_entity in referenced_entities:
            async for rule in self.authorize_action(referenced_entity.entity, session, "delete"):
                yield rule

    async def before_update(
        self,
        session: AuthorizedSession,
        referenced_entities: list[ReferencedEntity],
        conditions: EntityConditions | None,
        changes: dict[str, Any],
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        for referenced_entity in referenced_entities:
            async for rule in self.authorize_action(referenced_entity.entity, session, "update"):
                yield rule

    async def before_select(
        self,
        session: AuthorizedSession,
        referenced_entities: list[ReferencedEntity],
        conditions: EntityConditions | None,
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        for referenced_entity in referenced_entities:
            async for rule in self.authorize_action(referenced_entity.entity, session, "select"):
                yield rule


class OsoPostAuthHandler(PostAuthHandler):
    async def after_single_insert(self, session: AuthorizedSession, instance: Any) -> None:
        # Not relevant for Oso
        pass

    async def after_single_delete(self, session: AuthorizedSession, instance: Any) -> None:
        # Not relevant for Oso
        pass

    async def after_single_update(self, session: AuthorizedSession, instance: Any, changes: dict[str, Any]) -> None:
        # Not relevant for Oso
        pass

    async def after_many_insert(
        self, session: AuthorizedSession, entity: ReferencedEntity, values: list[dict[str, Any]]
    ) -> None:
        # Not relevant for Oso
        pass

    async def after_many_delete(
        self, session: AuthorizedSession, entity: ReferencedEntity, conditions: EntityConditions | None
    ) -> None:
        pass

    async def after_many_update(
        self,
        session: AuthorizedSession,
        entity: ReferencedEntity,
        conditions: EntityConditions | None,
        changes: dict[str, Any],
    ) -> None:
        # Not relevant for Oso
        pass
