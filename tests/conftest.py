import pytest
from pytest_mock import MockerFixture
from sqlalchemy import ForeignKey, create_engine, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, Session, backref, declarative_base, mapped_column, relationship

from sqlalchemy_auth_hooks.handler import SQLAlchemyAuthHandler
from sqlalchemy_auth_hooks.hooks import register_hooks
from sqlalchemy_auth_hooks.session import (
    UnauthorizedAsyncSession,
    UnauthorizedSession,
    AuthorizedSession,
    AuthorizedAsyncSession,
)

Base = declarative_base()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def auth_user():
    return "AuthUser"


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
def auth_handler(engine, mocker: MockerFixture):
    test_handler = mocker.Mock(spec=SQLAlchemyAuthHandler)
    register_hooks(test_handler)
    yield test_handler


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


@pytest.fixture(autouse=True)
def reset_handler(auth_handler):
    auth_handler.reset_mock()


def reorder_early_fixtures(metafunc):
    """
    Put fixtures with `pytest.mark.early` first during execution

    This allows patch of configurations before the application is initialized

    """
    for fixture_def in metafunc._arg2fixturedefs.values():  # type: ignore
        fixture_def = fixture_def[0]
        for mark in getattr(fixture_def.func, "pytestmark", []):
            if mark.name == "early":
                order = metafunc.fixturenames
                order.insert(0, order.pop(order.index(fixture_def.argname)))
                break


class UserGroup(Base):
    __tablename__ = "user_groups"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    group: Mapped["Group"] = relationship()
    user: Mapped["User"] = relationship()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int]
    groups: Mapped[list["UserGroup"]] = relationship(back_populates="user")


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    users: Mapped[list["UserGroup"]] = relationship(back_populates="group")
    parent_group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"))
    subgroups = relationship("Group", backref=backref("parent_group", remote_side=[id]))


def pytest_generate_tests(metafunc):
    reorder_early_fixtures(metafunc)


def pytest_configure(config):
    config.addinivalue_line("markers", "early: fixture should be ran early")
