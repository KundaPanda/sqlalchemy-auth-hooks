from pathlib import Path

import pytest
from oso import Oso
from sqlalchemy import create_engine, delete
from sqlalchemy.ext.asyncio import create_async_engine

from sqlalchemy_auth_hooks.hooks import register_hooks
from sqlalchemy_auth_hooks.oso.oso_handler import OsoHandler
from sqlalchemy_auth_hooks.oso.sqlalchemy_oso.auth import register_models
from sqlalchemy_auth_hooks.session import (
    AuthorizedAsyncSession,
    AuthorizedSession,
    UnauthorizedAsyncSession,
    UnauthorizedSession,
)
from tests.conftest import Base, Group, User, UserGroup


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def auth_user():
    class AuthUser:
        pass

    return AuthUser


@pytest.fixture(scope="session", autouse=True)
def engine(worker_id):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture
def authorized_session(engine, auth_user):
    return AuthorizedSession(engine, user=auth_user)


@pytest.fixture(scope="session")
async def async_engine(worker_id, anyio_backend):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine


@pytest.fixture
def authorized_async_session(async_engine, auth_user):
    return AuthorizedAsyncSession(async_engine, user=auth_user)


@pytest.fixture
@pytest.mark.early
def add_user(engine):
    user = User(name="John", age=42)
    with UnauthorizedSession(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
    return user


@pytest.fixture
@pytest.mark.early
def user_group(engine, add_user):
    with UnauthorizedSession(engine) as session:
        group = Group(name="Test Users")
        session.add(group)
        session.flush()
        group.users.append(UserGroup(user_id=add_user.id, group_id=group.id))
        session.commit()
        session.refresh(group)
        session.expunge(group)
    return group


@pytest.fixture
@pytest.mark.early
async def add_user_async(anyio_backend, async_engine):
    user = User(name="John", age=42)
    async with UnauthorizedAsyncSession(async_engine) as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
        session.expunge(user)
    return user


@pytest.fixture
@pytest.mark.early
async def user_group_async(async_engine, add_user_async):
    async with UnauthorizedAsyncSession(async_engine) as session:
        group = Group(name="Test Users")
        session.add(group)
        await session.flush()
        await session.refresh(group)
        ug = UserGroup(user_id=add_user_async.id, group_id=group.id)
        session.add(ug)
        await session.commit()
        await session.refresh(group)
        session.expunge(group)
    return group


@pytest.fixture(autouse=True)
def cleanup(engine):
    yield
    with UnauthorizedSession(engine) as session:
        session.execute(delete(User).where())
        session.execute(delete(Group).where())
        session.execute(delete(UserGroup).where())
        session.commit()


@pytest.fixture(autouse=True)
async def cleanup_async(anyio_backend, async_engine):
    yield
    async with UnauthorizedAsyncSession(async_engine) as session:
        await session.execute(delete(User).where())
        await session.execute(delete(Group).where())
        await session.execute(delete(UserGroup).where())
        await session.commit()


@pytest.fixture(scope="session")
def oso(auth_user):
    oso = Oso()
    register_models(oso, Base)
    oso.register_class(auth_user)
    base_path = Path(__file__).parent
    oso.load_files([base_path / "assets/authorization.polar"])
    return oso


@pytest.fixture
def oso_handler(oso):
    handler = OsoHandler(oso=oso, checked_permissions={User: "query"})
    register_hooks(handler)
    return handler
