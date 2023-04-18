from tests.conftest import User


def test_delete(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        session.delete(u)
        session.commit()
    auth_handler.on_single_delete.assert_called_once_with(authorized_session, u)


def test_delete_rollback(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        session.delete(u)
        session.rollback()
    auth_handler.on_single_delete.assert_not_called()


def test_create_rollback_implicit(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        session.delete(u)
    auth_handler.on_single_delete.assert_not_called()
