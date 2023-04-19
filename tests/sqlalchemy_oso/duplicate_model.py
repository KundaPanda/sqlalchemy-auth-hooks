from sqlalchemy.orm import Mapped, mapped_column

from .test_duplicate_models import Base


class Post(Base):
    __tablename__ = "posts_one"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin: Mapped[bool] = mapped_column(nullable=False)
