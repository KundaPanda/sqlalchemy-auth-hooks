from sqlalchemy import inspect
from sqlalchemy.sql.operators import eq

from sqlalchemy_auth_hooks.references import ReferenceConditions, ReferencedEntity
from sqlalchemy_auth_hooks.session import UnauthorizedSession
from tests.conftest import Group
from tests.core.conftest import User


def test_delete(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = session.get(User, add_user.id)
        session.delete(user)
        session.commit()
    auth_handler.before_delete.assert_called_once_with(
        authorized_session,
        [ReferencedEntity(entity=inspect(User), selectable=User.__table__)],
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": add_user.id}}),
    )


async def test_delete_async(async_engine, add_user_async, auth_handler, authorized_async_session):
    async with authorized_async_session as session:
        user = await session.get(User, add_user_async.id)
        await session.delete(user)
        await session.commit()
    auth_handler.before_delete.assert_called_once_with(
        authorized_async_session.sync_session,
        [ReferencedEntity(entity=inspect(User), selectable=User.__table__)],
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": add_user_async.id}}),
    )


def test_delete_many(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = User(name="Elvis", age=98)
        user2 = User(name="Alice", age=65)
        session.add_all([user, user2])
        session.commit()
        session.refresh(user)
        session.refresh(user2)
        orig_user = session.get(User, add_user.id)

        session.delete(orig_user)
        session.delete(user)
        session.delete(user2)
        session.commit()

    auth_handler.before_delete.assert_any_call(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": add_user.id}}),
    )

    auth_handler.before_delete.assert_any_call(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": user.id}}),
    )

    auth_handler.before_delete.assert_any_call(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": user2.id}}),
    )


def test_delete_many_different(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        user = session.get(User, add_user.id)
        group = session.get(Group, user_group.id)
        session.delete(user)
        session.delete(group)
        session.commit()
    auth_handler.before_delete.assert_any_call(
        authorized_session,
        [ReferencedEntity(inspect(User), User.__table__)],
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": add_user.id}}),
    )
    auth_handler.before_delete.assert_any_call(
        authorized_session,
        [ReferencedEntity(inspect(Group), Group.__table__)],
        ReferenceConditions(selectable=Group.__table__, conditions={"id": {"operator": eq, "value": user_group.id}}),
    )


def test_delete_rollback(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = session.get(User, add_user.id)
        session.delete(user)
        session.rollback()
    auth_handler.before_delete.assert_not_called()


def test_delete_rollback_implicit(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = session.get(User, add_user.id)
        session.delete(user)
    auth_handler.before_delete.assert_not_called()
