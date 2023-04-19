from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.schema import Table

ModelBase = declarative_base(name="ModelBase")


class Category(ModelBase):
    __tablename__ = "category"

    name: Mapped[str] = mapped_column(String, primary_key=True)

    tags: Mapped[list["Tag"]] = relationship(secondary="category_tags", back_populates="categories")
    users: Mapped[list["User"]] = relationship(secondary="category_users")


category_users = Table(
    "category_users",
    ModelBase.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("category_name", String, ForeignKey("category.name")),
)

category_tags = Table(
    "category_tags",
    ModelBase.metadata,
    Column("tag_name", String, ForeignKey("tags.name")),
    Column("category_name", String, ForeignKey("category.name")),
)


class Tag(ModelBase):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(primary_key=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])

    users: Mapped[list["User"]] = relationship(secondary="user_tags", back_populates="tags")
    categories: Mapped[list["Category"]] = relationship(secondary="category_tags", back_populates="tags")

    # If provided, posts in this tag always have the public access level.
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)


post_tags = Table(
    "post_tags",
    ModelBase.metadata,
    Column("post_id", Integer, ForeignKey("posts.id")),
    Column("tag_id", Integer, ForeignKey("tags.name")),
)

user_tags = Table(
    "user_tags",
    ModelBase.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("tag_id", Integer, ForeignKey("tags.name")),
)

post_users = Table(
    "post_users",
    ModelBase.metadata,
    Column("post_id", Integer, ForeignKey("posts.id")),
    Column("user_id", Integer, ForeignKey("users.id")),
)


class Post(ModelBase):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    contents: Mapped[str]
    title: Mapped[str] = mapped_column(nullable=True)
    access_level = mapped_column(Enum("public", "private"), default="private")

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped["User"] = relationship(backref="posts")

    users: Mapped[list["User"]] = relationship(secondary=post_users)

    needs_moderation: Mapped[bool] = mapped_column(default=False)

    tags: Mapped[list["Tag"]] = relationship(secondary=post_tags, backref="posts")


class User(ModelBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False)

    is_moderator: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_banned: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Single tag
    tag_name: Mapped[int] = mapped_column(ForeignKey("tags.name"), nullable=True)
    tag: Mapped["Tag"] = relationship(foreign_keys=[tag_name])

    # Many tags
    tags: Mapped[list["Tag"]] = relationship(secondary=user_tags, back_populates="users")
