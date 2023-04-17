from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from sqlalchemy_auth_hooks.handler import ReferencedEntity
from tests.conftest import User, UserGroup


def test_simple_get(engine, add_user, auth_handler):
    with Session(engine) as session:
        session.get(User, add_user.id)
    mapper = inspect(User)
    auth_handler.on_select.assert_called_once_with(
        [ReferencedEntity(entity=mapper, keys={"id": add_user.id}, selectable=User.__table__)]
    )


def test_simple_select(engine, add_user, auth_handler):
    with Session(engine) as session:
        session.execute(select(User).filter_by(id=add_user.id))
    mapper = inspect(User)
    auth_handler.on_select.assert_called_once_with(
        [ReferencedEntity(entity=mapper, keys={"id": add_user.id}, selectable=User.__table__)]
    )


def test_simple_select_where(engine, add_user, auth_handler):
    with Session(engine) as session:
        session.execute(select(User).where(User.id == add_user.id))
    mapper = inspect(User)
    auth_handler.on_select.assert_called_once_with(
        [ReferencedEntity(entity=mapper, keys={"id": add_user.id}, selectable=User.__table__)]
    )


def test_simple_select_column_only(engine, add_user, auth_handler):
    with Session(engine) as session:
        session.execute(select(User.name).filter_by(id=add_user.id))
    mapper = inspect(User)
    auth_handler.on_select.assert_called_once_with(
        [ReferencedEntity(entity=mapper, keys={"id": add_user.id}, selectable=User.__table__)]
    )


def test_select_multiple_pk(engine, add_user, user_group, auth_handler):
    with Session(engine) as session:
        session.execute(select(UserGroup).filter_by(user_id=add_user.id, group_id=user_group.id))
    mapper = inspect(UserGroup)
    auth_handler.on_select.assert_called_once_with(
        [
            ReferencedEntity(
                entity=mapper, keys={"user_id": add_user.id, "group_id": user_group.id}, selectable=UserGroup.__table__
            )
        ]
    )
