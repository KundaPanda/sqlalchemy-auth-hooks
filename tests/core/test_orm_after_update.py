from tests.core.conftest import User


def test_update(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.commit()
    post_auth_handler.after_single_update.assert_called_once_with(authorized_session, u, {"name": "Jane"})


async def test_update_async(engine, add_user_async, post_auth_handler, authorized_async_session):
    async with authorized_async_session as session:
        u = await session.get(User, add_user_async.id)
        u.name = "Jane"
        await session.commit()
        await session.refresh(u)
    post_auth_handler.after_single_update.assert_called_once_with(
        authorized_async_session.sync_session, u, {"name": "Jane"}
    )


def test_update_multiple_same_column(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.flush()
        u.name = "Jill"
        session.commit()
    post_auth_handler.after_single_update.assert_any_call(authorized_session, u, {"name": "Jane"})
    post_auth_handler.after_single_update.assert_called_with(authorized_session, u, {"name": "Jill"})
    assert post_auth_handler.after_single_update.call_count == 2


def test_update_multiple_different_columns(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        u.age = 43
        session.commit()
    post_auth_handler.after_single_update.assert_called_with(authorized_session, u, {"name": "Jane", "age": 43})


def test_update_rollback(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
        session.rollback()
    post_auth_handler.after_single_update.assert_not_called()


def test_update_rollback_implicit(engine, add_user, post_auth_handler, authorized_session):
    with authorized_session as session:
        u = session.get(User, add_user.id)
        u.name = "Jane"
    post_auth_handler.after_single_update.assert_not_called()
