from tests.core.conftest import User


def test_delete(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        session.delete(u)
        session.commit()
    post_auth_handler.after_single_delete.assert_called_once_with(authorized_session, u)


async def test_delete_async(async_engine, add_user_async, post_auth_handler, authorized_async_session):
    async with authorized_async_session as session:
        u = await session.get(User, add_user_async.id)
        await session.delete(u)
        await session.commit()
    post_auth_handler.after_single_delete.assert_called_once_with(authorized_async_session.sync_session, u)


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
