from sqlalchemy.orm import Session

from tests.conftest import User


def test_create_session(engine, auth_handler):
    user = User(name="John", age=42)
    with Session(engine) as session:
        session.add(user)
        session.commit()
        assert user.id is not None
        auth_handler.on_single_create.assert_called_once_with(user)


def test_create_rollback(engine, auth_handler):
    user = User(name="John", age=42)
    with Session(engine) as session:
        session.add(user)
        session.rollback()
        assert user.id is None
    auth_handler.on_single_create.assert_not_called()


def test_create_rollback_implicit(engine, auth_handler):
    user = User(name="John", age=42)
    with Session(engine) as session:
        session.add(user)
        assert user.id is None
    auth_handler.on_single_create.assert_not_called()
