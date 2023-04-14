import pytest
from sqlalchemy.orm import Session

from tests.conftest import User


@pytest.fixture
def add_user(engine):
    user = User(name="John", age=42)
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
    return user


def test_delete(engine, add_user, auth_handler):
    with Session(engine) as session:
        u = session.get(User, add_user.id)
        session.delete(u)
        session.commit()
    auth_handler.on_delete.assert_called_once_with(u)


def test_delete_rollback(engine, add_user, auth_handler):
    with Session(engine) as session:
        u = session.get(User, add_user.id)
        session.delete(u)
        session.rollback()
    auth_handler.on_delete.assert_not_called()


def test_create_rollback_implicit(engine, add_user, auth_handler):
    with Session(engine) as session:
        u = session.get(User, add_user.id)
        session.delete(u)
    auth_handler.on_delete.assert_not_called()
