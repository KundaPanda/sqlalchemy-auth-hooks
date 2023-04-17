from sqlalchemy import inspect, update, func
from sqlalchemy.orm import Session
from sqlalchemy.sql.operators import eq, startswith_op

from sqlalchemy_auth_hooks.handler import ReferencedEntity
from tests.conftest import User


def test_update(engine, auth_handler, add_user):
    with Session(engine) as session:
        session.execute(update(User).where(User.id == add_user.id).values(name="John"))
        session.commit()
    auth_handler.on_update.assert_called_once_with(
        ReferencedEntity(
            entity=inspect(User),
            keys={"id": add_user.id},
            selectable=User.__table__,
            conditions={"id": {"operator": eq, "value": add_user.id}},
        ),
        {"name": "John"},
    )


def test_update_all(engine, auth_handler, add_user):
    with Session(engine) as session:
        session.execute(update(User).values(name="John", age=10))
        session.commit()
    auth_handler.on_update.assert_called_once_with(
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        {"name": "John", "age": 10},
    )


def test_update_condition(engine, auth_handler, add_user):
    with Session(engine) as session:
        session.execute(update(User).where(User.name.startswith("J")).values(name="John", age=10))
        session.commit()
    auth_handler.on_update.assert_called_once_with(
        ReferencedEntity(
            entity=inspect(User),
            selectable=User.__table__,
            conditions={"name": {"operator": startswith_op, "value": "J"}},
        ),
        {"name": "John", "age": 10},
    )
