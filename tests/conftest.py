import pytest
from pytest_mock import MockerFixture
from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship, backref

from sqlalchemy_auth_hooks.handler import SQLAlchemyAuthHandler
from sqlalchemy_auth_hooks.hooks import register_hooks

Base = declarative_base()


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


@pytest.fixture(scope="session", autouse=True)
def engine(worker_id):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture
def auth_handler(engine, mocker: MockerFixture):
    test_handler = mocker.Mock(spec=SQLAlchemyAuthHandler)
    register_hooks(test_handler)
    yield test_handler


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


def pytest_generate_tests(metafunc):
    reorder_early_fixtures(metafunc)


def pytest_configure(config):
    config.addinivalue_line("markers", "early: fixture should be ran early")
