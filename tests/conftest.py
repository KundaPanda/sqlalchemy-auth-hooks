import pytest
from pytest_mock import MockerFixture
from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

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
