from sqlalchemy import delete, inspect
from sqlalchemy.sql.operators import eq

from sqlalchemy_auth_hooks.references import ReferencedEntity, ReferenceConditions
from tests.core.conftest import User


def test_delete(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        session.execute(delete(User).where(User.id == u.id))
        session.commit()
    post_auth_handler.after_many_delete.assert_called_once_with(
        authorized_session,
        ReferencedEntity(entity=inspect(User), selectable=User.__table__),
        ReferenceConditions(selectable=User.__table__, conditions={"id": {"operator": eq, "value": u.id}}),
    )


def test_delete_rollback(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        session.delete(u)
        session.rollback()
    post_auth_handler.after_single_delete.assert_not_called()


def test_create_rollback_implicit(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        session.delete(u)
    post_auth_handler.after_single_delete.assert_not_called()
