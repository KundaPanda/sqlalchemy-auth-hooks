from sqlalchemy import delete, inspect
from sqlalchemy.sql.operators import eq

from sqlalchemy_auth_hooks.references import ReferenceConditions, ReferencedEntity
from tests.core.conftest import User


def test_delete(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(delete(User).where(User.id == add_user.id))
        session.commit()
    post_auth_handler.after_many_delete.assert_called_once_with(
        authorized_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": add_user.id}}),
    )


async def test_delete_async(engine, add_user_async, post_auth_handler, authorized_async_session):
    async with authorized_async_session as session:
        await session.execute(delete(User).where(User.id == add_user_async.id))
        await session.commit()
    post_auth_handler.after_many_delete.assert_called_once_with(
        authorized_async_session.sync_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": add_user_async.id}}),
    )


def test_delete_rollback(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(delete(User).where(User.id == add_user.id))
        session.rollback()
    post_auth_handler.after_many_delete.assert_not_called()


def test_create_rollback_implicit(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(delete(User).where(User.id == add_user.id))
    post_auth_handler.after_many_delete.assert_not_called()
