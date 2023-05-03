from sqlalchemy import inspect, select
from sqlalchemy.sql.operators import eq

from sqlalchemy_auth_hooks.references import ReferenceConditions, ReferencedEntity
from tests.core.conftest import Group, User, UserGroup


def test_join_lazyload(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        user: User = session.scalar(select(User).limit(1))
        _ = user.groups
        _ = user.groups[0].group.name
    assert auth_handler.before_select.call_count == 3
    auth_handler.before_select.assert_any_call(
        authorized_session,
        [ReferencedEntity(entity=inspect(User), selectable=User.__table__)],
        None,
    )
    auth_handler.before_select.assert_any_call(
        authorized_session,
        [ReferencedEntity(entity=inspect(UserGroup), selectable=UserGroup.__table__)],
        ReferenceConditions(
            selectable=UserGroup.__table__,
            conditions={"user_id": {"operator": eq, "value": 1}},
        ),
    )
    # Only one group should be queried
    auth_handler.before_select.assert_called_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=inspect(Group),
                selectable=Group.__table__,
            )
        ],
        ReferenceConditions(
            selectable=Group.__table__,
            conditions={"id": {"operator": eq, "value": 1}},
        ),
    )
