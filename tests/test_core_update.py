from sqlalchemy import update, inspect
from sqlalchemy.orm import Session

from sqlalchemy_auth_hooks.handler import ReferencedEntity
from tests.conftest import User


def test_update(engine, auth_handler, add_user):
    with Session(engine) as session:
        session.execute(update(User).where(User.id == add_user.id).values(name="John"))
        session.commit()
    auth_handler.on_update.assert_called_once_with(
        ReferencedEntity(entity=inspect(User), keys={"id": add_user.id}, selectable=User.__table__),
        {"name": "John"},
    )
