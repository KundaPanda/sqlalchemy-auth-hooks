from pytest_mock import MockerFixture
from sqlalchemy import insert, inspect, select, literal, true
from sqlalchemy.orm import ORMExecuteState
from sqlalchemy.sql.functions import concat
from sqlalchemy.sql.operators import startswith_op

from sqlalchemy_auth_hooks.references import ReferenceCondition, ReferencedEntity
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


def test_insert_from_select(engine, hooks, auth_handler, add_user, authorized_session, mocker: MockerFixture):
    spy = mocker.spy(hooks.authorizer, "authorize_select")
    with authorized_session as session:
        session.execute(insert(User).from_select(["name", "age"], select(User.name + literal(" second"), User.age)))
        session.commit()
    auth_handler.before_insert.assert_called_once_with(
        authorized_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        [],
    )
    spy.assert_called_once()
    exec_state: ORMExecuteState = spy.call_args[0][0]
    expected = (
        select(User.name + literal(" second"), User.age)
        .where(true())
        .compile(compile_kwargs={"literal_binds": True})
        .string
    )
    assert exec_state.statement.compile(compile_kwargs={"literal_binds": True}).string == expected
