from sqlalchemy import inspect, update
from sqlalchemy.sql.operators import eq, startswith_op

from sqlalchemy_auth_hooks.handler import ReferencedEntity
from sqlalchemy_auth_hooks.references import ReferenceConditions
from tests.core.conftest import User


def test_update(engine, post_auth_handler, add_user, authorized_session):
    with authorized_session as session:
        session.execute(update(User).where(User.id == add_user.id).values(name="John"))
        session.commit()
    selectable = User.__table__
    post_auth_handler.after_core_update.assert_called_once_with(
        ReferencedEntity(
            entity=inspect(User),
            selectable=selectable,
        ),
        ReferenceConditions(selectable, {"id": {"operator": eq, "value": 1}}),
        {"name": "John"},
    )


def test_update_all(engine, post_auth_handler, add_user, authorized_session):
    with authorized_session as session:
        session.execute(update(User).values(name="John", age=10))
        session.commit()
    post_auth_handler.after_core_update.assert_called_once_with(
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        None,
        {"name": "John", "age": 10},
    )


def test_update_condition(engine, post_auth_handler, add_user, authorized_session):
    with authorized_session as session:
        session.execute(update(User).where(User.name.startswith("J")).values(name="John", age=10))
        session.commit()
    selectable = User.__table__
    post_auth_handler.after_core_update.assert_called_once_with(
        ReferencedEntity(
            entity=inspect(User),
            selectable=selectable,
        ),
        ReferenceConditions(selectable, {"name": {"operator": startswith_op, "value": "J"}}),
        {"name": "John", "age": 10},
    )
