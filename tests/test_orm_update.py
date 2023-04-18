from tests.conftest import User


def test_update(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.commit()
    auth_handler.on_single_update.assert_called_once_with(authorized_session, u, {"name": "Jane"})


def test_update_multiple_same_column(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.flush()
        u.name = "Jill"
        session.commit()
    auth_handler.on_single_update.assert_any_call(authorized_session, u, {"name": "Jane"})
    auth_handler.on_single_update.assert_called_with(authorized_session, u, {"name": "Jill"})
    assert auth_handler.on_single_update.call_count == 2


def test_update_multiple_different_columns(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        u.age = 43
        session.commit()
    auth_handler.on_single_update.assert_called_with(authorized_session, u, {"name": "Jane", "age": 43})


def test_update_rollback(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.rollback()
    auth_handler.on_single_update.assert_not_called()


def test_update_rollback_implicit(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
    auth_handler.on_single_update.assert_not_called()
