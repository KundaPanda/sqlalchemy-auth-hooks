from sqlalchemy import insert, inspect

from sqlalchemy_auth_hooks.references import ReferencedEntity
from tests.conftest import User


def test_create_session(engine, post_auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(insert(User).values(name="John", age=42))
        session.commit()
    post_auth_handler.after_many_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        [{"name": "John", "age": 42}],
    )


def test_create_session_tuple(engine, post_auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(insert(User).values((100, "John", 42)))
        session.commit()
    post_auth_handler.after_many_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        [{"name": "John", "age": 42, "id": 100}],
    )


def test_create_session_dict(engine, post_auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(insert(User).values({"name": "John", "age": 42}))
        session.commit()
    post_auth_handler.after_many_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        [{"name": "John", "age": 42}],
    )


def test_create_many_session(engine, post_auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(insert(User).values([dict(name="John", age=42), dict(name="Jane", age=43)]))
        session.commit()
    post_auth_handler.after_many_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        [{"name": "John", "age": 42}, {"name": "Jane", "age": 43}],
    )
