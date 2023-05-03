from tests.core.conftest import User


def test_create_session(engine, post_auth_handler, authorized_session):
    user = User(name="John", age=42)
    with authorized_session as session:
        session.add(user)
        session.commit()
        assert user.id is not None
        post_auth_handler.after_single_insert.assert_called_once_with(authorized_session, user)


async def test_create_async(async_engine, post_auth_handler, authorized_async_session):
    user = User(name="John", age=42)
    async with authorized_async_session as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert user.id is not None
        post_auth_handler.after_single_insert.assert_called_once_with(authorized_async_session.sync_session, user)


def test_create_authorization_check(engine, post_auth_handler, authorized_session):
    user = User(name="John", age=42)
    with authorized_session as session:
        session.add(user)
        session.commit()
        assert user.id is not None
        post_auth_handler.after_single_insert.assert_called_once_with(authorized_session, user)


def test_create_rollback(engine, post_auth_handler, authorized_session):
    user = User(name="John", age=42)
    with authorized_session as session:
        session.add(user)
        session.rollback()
        assert user.id is None
    post_auth_handler.after_single_insert.assert_not_called()


def test_create_rollback_implicit(engine, post_auth_handler, authorized_session):
    user = User(name="John", age=42)
    with authorized_session as session:
        session.add(user)
        assert user.id is None
    post_auth_handler.after_single_insert.assert_not_called()
