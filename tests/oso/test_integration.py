from sqlalchemy_auth_hooks.orm_hooks import register_hooks
from sqlalchemy_auth_hooks.oso.oso_handler import OsoAuthHandler, OsoPostAuthHandler
from tests.core.conftest import User


def test_select(add_user, authorized_session, oso_handler):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        assert u is not None
        session.expunge(u)
    assert u.name == "John"


def test_select_no_permission(add_user, oso, authorized_session):
    handler = OsoAuthHandler(oso=oso, checked_permissions={User: "other_permission"})
    post_auth_handler = OsoPostAuthHandler()
    register_hooks(handler, post_auth_handler)
    with authorized_session as session:
        u = session.get(User, add_user.id)
    assert u is None
