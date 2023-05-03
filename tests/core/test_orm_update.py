from sqlalchemy import inspect
from sqlalchemy.sql.operators import eq

from sqlalchemy_auth_hooks.references import ReferenceConditions, ReferencedEntity
from tests.core.conftest import User


def test_update(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.commit()
    auth_handler.before_update.assert_called_once_with(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(User.__table__, {"id": {"operator": eq, "value": add_user.id}}),
        {"name": "Jane"},
    )


async def test_update_async(async_engine, add_user_async, auth_handler, authorized_async_session):
    async with authorized_async_session as session:
        u = await session.get(User, add_user_async.id)
        u.name = "Jane"
        await session.commit()
    auth_handler.before_update.assert_called_once_with(
        authorized_async_session.sync_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(User.__table__, {"id": {"operator": eq, "value": add_user_async.id}}),
        {"name": "Jane"},
    )


def test_update_multiple_same_column(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.flush()
        u.name = "Jill"
        session.commit()
    auth_handler.before_update.assert_any_call(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(User.__table__, {"id": {"operator": eq, "value": add_user.id}}),
        {"name": "Jane"},
    )
    auth_handler.before_update.assert_called_with(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(User.__table__, {"id": {"operator": eq, "value": add_user.id}}),
        {"name": "Jill"},
    )
    assert auth_handler.before_update.call_count == 2


def test_update_multiple_different_columns(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        u.age = 43
        session.commit()
    auth_handler.before_update.assert_called_with(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(User.__table__, {"id": {"operator": eq, "value": add_user.id}}),
        {"name": "Jane", "age": 43},
    )


def test_update_rollback(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.rollback()
    auth_handler.before_update.assert_not_called()


def test_update_rollback_implicit(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
    auth_handler.before_update.assert_not_called()
