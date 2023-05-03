from sqlalchemy import delete, inspect, true
from sqlalchemy.sql.operators import eq, gt, is_true

from sqlalchemy_auth_hooks.references import (
    LiteralExpression,
    ReferenceCondition,
    ReferencedEntity,
    UnaryCondition,
)
from tests.core.conftest import User


def test_delete(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(delete(User).where(User.name == "John"))
        session.commit()
    auth_handler.before_delete.assert_called_once_with(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceCondition(
            left=User.__table__.c.name,
            operator=eq,
            right=LiteralExpression("John"),
        ),
    )


async def test_delete_async(add_user_async, auth_handler, authorized_async_session):
    async with authorized_async_session as session:
        await session.execute(delete(User).where(User.name == "John"))
        await session.commit()
    auth_handler.before_delete.assert_called_once_with(
        authorized_async_session.sync_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceCondition(
            left=User.__table__.c.name,
            operator=eq,
            right=LiteralExpression("John"),
        ),
    )


def test_delete_all(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(delete(User).where())
        session.commit()
    auth_handler.before_delete.assert_called_once_with(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        None,
    )


def test_delete_all2(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(delete(User).where(true()))
        session.commit()
    auth_handler.before_delete.assert_called_once_with(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        None,
    )


def test_delete_dynamic_condition(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(delete(User).where(User.name > User.id))
        session.commit()
    auth_handler.before_delete.assert_called_once_with(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceCondition(
            left=User.__table__.c.name,
            operator=gt,
            right=User.__table__.c.id,
        ),
    )
