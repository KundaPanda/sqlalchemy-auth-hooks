from typing import Any, AsyncIterator, cast

import structlog
from oso import Oso
from sqlalchemy import false, inspect
from sqlalchemy.orm import Mapper
from sqlalchemy.sql.roles import ExpressionElementRole

from sqlalchemy_auth_hooks.handler import SQLAlchemyAuthHandler
from sqlalchemy_auth_hooks.oso.sqlalchemy_oso.auth import authorize_model
from sqlalchemy_auth_hooks.references import EntityConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import AuthorizedSession

logger = structlog.get_logger()


class OsoHandler(SQLAlchemyAuthHandler):
    def __init__(
        self, oso: Oso, checked_permissions: dict[type[Any], str], default_checked_permission: str | None = None
    ) -> None:
        self.oso = oso
        self.checked_permissions: dict[Mapper[Any], str] = {
            cast(Mapper[Any], inspect(entity)).mapper: permission for entity, permission in checked_permissions.items()
        }
        self.default_checked_permission = default_checked_permission

    async def before_select(
        self,
        session: AuthorizedSession,
        referenced_entities: list[ReferencedEntity],
        conditions: EntityConditions | None,
    ) -> AsyncIterator[tuple[Mapper[Any], ExpressionElementRole[Any]]]:
        for referenced_entity in referenced_entities:
            checked_permission = self.checked_permissions.get(referenced_entity.entity, self.default_checked_permission)
            if checked_permission is None:
                logger.warning(f"No permission to check for {referenced_entity.entity}")
                yield referenced_entity.entity, false()
                return
            filter_ = authorize_model(
                self.oso, session.user, checked_permission, session, referenced_entity.entity.class_
            )
            if filter_ is not None:
                logger.debug("Filtering %s with %s", referenced_entity.entity, filter_)
                yield referenced_entity.entity, filter_
            else:
                logger.warning("No filter for %s", referenced_entity.entity)

    async def after_single_create(self, session: AuthorizedSession, instance: Any) -> None:
        # Not relevant for Oso
        pass

    async def after_single_delete(self, session: AuthorizedSession, instance: Any) -> None:
        # Not relevant for Oso
        pass

    async def after_single_update(self, session: AuthorizedSession, instance: Any, changes: dict[str, Any]) -> None:
        # Not relevant for Oso
        pass

    async def after_core_update(
        self,
        session: AuthorizedSession,
        referenced_entity: ReferencedEntity,
        conditions: EntityConditions | None,
        changes: dict[str, Any],
    ) -> None:
        # Not relevant for Oso
        pass
