import logging

import structlog
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, backref, declarative_base, mapped_column, relationship
from structlog.dev import ConsoleRenderer

logging.basicConfig(level=logging.DEBUG)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logging.getLogger("aiosqlite").setLevel(logging.INFO)
logging.getLogger("asyncio").setLevel(logging.INFO)


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


def pytest_generate_tests(metafunc):
    reorder_early_fixtures(metafunc)


def pytest_configure(config):
    config.addinivalue_line("markers", "early: fixture should be ran early")
