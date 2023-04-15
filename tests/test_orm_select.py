import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from sqlalchemy_auth_hooks.handler import ReferencedEntity
from tests.conftest import Group, User, UserGroup


@pytest.fixture
def add_user(engine, auth_handler):
    user = User(name="John", age=42)
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
    auth_handler.reset_mock()
    return user


@pytest.fixture
def user_group(engine, add_user, auth_handler):
    with Session(engine) as session:
        group = Group(name="Test Users")
        session.add(group)
        session.flush()
        group.users.append(UserGroup(user_id=add_user.id, group_id=group.id))
        session.commit()
        session.refresh(group)
        session.expunge(group)
    auth_handler.reset_mock()
    return group


def test_simple_get(engine, add_user, auth_handler):
    with Session(engine) as session:
        session.get(User, add_user.id)
    mapper = inspect(User)
    auth_handler.on_select.assert_called_once_with(ReferencedEntity(entity=mapper, keys={"id": add_user.id}))


def test_simple_select(engine, add_user, auth_handler):
    with Session(engine) as session:
        session.execute(select(User).filter_by(id=add_user.id))
    mapper = inspect(User)
    auth_handler.on_select.assert_called_once_with(ReferencedEntity(entity=mapper, keys={"id": add_user.id}))


def test_simple_select_where(engine, add_user, auth_handler):
    with Session(engine) as session:
        session.execute(select(User).where(User.id == add_user.id))
    mapper = inspect(User)
    auth_handler.on_select.assert_called_once_with(ReferencedEntity(entity=mapper, keys={"id": add_user.id}))


def test_simple_select_column_only(engine, add_user, auth_handler):
    with Session(engine) as session:
        session.execute(select(User.name).filter_by(id=add_user.id))
    mapper = inspect(User)
    auth_handler.on_select.assert_called_once_with(ReferencedEntity(entity=mapper, keys={"id": add_user.id}))


def test_select_multiple_pk(engine, add_user, auth_handler, user_group):
    with Session(engine) as session:
        session.execute(select(UserGroup).filter_by(user_id=add_user.id, group_id=user_group.id))
    mapper = inspect(UserGroup)
    auth_handler.on_select.assert_called_once_with(
        ReferencedEntity(entity=mapper, keys={"user_id": add_user.id, "group_id": user_group.id})
    )
