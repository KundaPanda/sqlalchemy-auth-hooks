import pytest
from oso import Oso
from polar.exceptions import DuplicateClassAliasError, OsoError
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base

from sqlalchemy_auth_hooks.oso.sqlalchemy_oso.auth import register_models

Base = declarative_base(name="Base")


class Post(Base):
    __tablename__ = "posts_two"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)


def test_duplicate_models(oso):
    from .duplicate_model import Post as DuplicatePost

    try:  # SQLAlchemy 1.4
        engine = create_engine("sqlite:///:memory:", enable_from_linting=False)
    except TypeError:  # SQLAlchemy 1.3
        engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with pytest.raises(OsoError):
        oso = Oso()
        register_models(oso, Base)

    oso = Oso()
    oso.register_class(DuplicatePost, name="duplicate::Post")
    register_models(oso, Base)

    for m in [Post, DuplicatePost]:
        with pytest.raises(DuplicateClassAliasError):
            oso.register_class(m)
