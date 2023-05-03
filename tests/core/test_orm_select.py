from sqlalchemy import inspect
from sqlalchemy.sql.operators import and_, eq

from sqlalchemy_auth_hooks.references import (
    CompositeCondition,
    LiteralExpression,
    ReferenceCondition,
    ReferencedEntity,
)
from tests.core.conftest import User, UserGroup


def test_simple_get(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.get(User, add_user.id)
    mapper = inspect(User)
    selectable = User.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        ReferenceCondition(
            left=selectable.c.id,
            operator=eq,
            right=LiteralExpression(add_user.id),
        ),
    )


async def test_simple_get_async(async_engine, add_user_async, auth_handler, authorized_async_session):
    async with authorized_async_session as session:
        await session.get(User, add_user_async.id)
    mapper = inspect(User)
    selectable = User.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_async_session.sync_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        ReferenceCondition(
            left=selectable.c.id,
            operator=eq,
            right=LiteralExpression(add_user_async.id),
        ),
    )


def test_select_get(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.get(UserGroup, (add_user.id, user_group.id))
    mapper = inspect(UserGroup)
    selectable = UserGroup.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        CompositeCondition(
            operator=and_,
            conditions=[
                ReferenceCondition(
                    left=selectable.c.user_id,
                    operator=eq,
                    right=LiteralExpression(add_user.id),
                ),
                ReferenceCondition(
                    left=selectable.c.group_id,
                    operator=eq,
                    right=LiteralExpression(user_group.id),
                ),
            ],
        ),
    )
