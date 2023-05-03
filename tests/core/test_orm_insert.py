from sqlalchemy import inspect
from sqlalchemy.sql.operators import eq

from sqlalchemy_auth_hooks.references import ReferenceConditions, ReferencedEntity
from tests.conftest import Group
from tests.core.conftest import User


def test_insert(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = User(name="Elvis", age=98)
        session.add(user)
        session.commit()
    auth_handler.before_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(inspect(User), User.__table__),
        [{"age": 98, "name": "Elvis"}],
    )


def test_insert_many(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = User(name="Elvis", age=98)
        user2 = User(name="Alice", age=65)
        session.add_all([user, user2])
        session.commit()

    # Note that this is not optimized
    auth_handler.before_insert.assert_any_call(
        authorized_session,
        ReferencedEntity(inspect(User), User.__table__),
        [{"age": 98, "name": "Elvis"}],
    )
    auth_handler.before_insert.assert_any_call(
        authorized_session,
        ReferencedEntity(inspect(User), User.__table__),
        [{"age": 65, "name": "Alice"}],
    )


def test_insert_many_different(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = User(name="Elvis", age=98)
        group = Group(name="Test Users")
        session.add_all([user, group])
        session.commit()
    auth_handler.before_insert.assert_any_call(
        authorized_session,
        ReferencedEntity(inspect(User), User.__table__),
        [{"age": 98, "name": "Elvis"}],
    )
    auth_handler.before_insert.assert_any_call(
        authorized_session,
        ReferencedEntity(inspect(Group), Group.__table__),
        [{"name": "Test Users"}],
    )


def test_insert_rollback(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = User(name="Elvis", age=98)
        session.add(user)
        session.rollback()
    auth_handler.before_insert.assert_not_called()


def test_insert_rollback_implicit(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        user = User(name="Elvis", age=98)
        session.add(user)
    auth_handler.before_insert.assert_not_called()
