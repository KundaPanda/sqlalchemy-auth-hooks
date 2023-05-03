from sqlalchemy import insert, inspect
from sqlalchemy.sql.operators import startswith_op

from sqlalchemy_auth_hooks.references import ReferenceConditions, ReferencedEntity
from tests.core.conftest import User


def test_insert(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(insert(User).values(name="Jane", age=10))
        session.commit()
    auth_handler.before_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(inspect(User), User.__table__),
        [{"name": "Jane", "age": 10}],
    )


async def test_insert_async(async_engine, add_user_async, auth_handler, authorized_async_session):
    async with authorized_async_session as session:
        await session.execute(insert(User).values(name="Jane", age=10))
        await session.commit()
    auth_handler.before_insert.assert_called_once_with(
        authorized_async_session.sync_session,
        ReferencedEntity(inspect(User), User.__table__),
        [{"name": "Jane", "age": 10}],
    )


def test_insert_tuple(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(insert(User).values((100, "Jane", 10)))
        session.commit()
    auth_handler.before_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(inspect(User), User.__table__),
        [{"id": 100, "name": "Jane", "age": 10}],
    )


def test_insert_dict(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(insert(User).values({"name": "Jane", "age": 10}))
        session.commit()
    auth_handler.before_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(inspect(User), User.__table__),
        [{"name": "Jane", "age": 10}],
    )


def test_insert_many(engine, auth_handler, add_user, authorized_session):
    with authorized_session as session:
        session.execute(insert(User).values([dict(name="John", age=10), dict(name="Jane", age=10)]))
        session.commit()
    auth_handler.before_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        [{"name": "John", "age": 10}, {"name": "Jane", "age": 10}],
    )
