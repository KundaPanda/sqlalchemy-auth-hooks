from sqlalchemy import inspect, select
from sqlalchemy.orm import aliased, joinedload, selectinload
from sqlalchemy.sql.operators import eq, in_op

from sqlalchemy_auth_hooks.handler import ReferencedEntity
from sqlalchemy_auth_hooks.references import ReferenceConditions
from tests.core.conftest import Group, User, UserGroup


def test_join(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(User).join(User.groups).join(UserGroup.group))
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(entity=inspect(User), selectable=User.__table__),
            ReferencedEntity(entity=inspect(UserGroup), selectable=UserGroup.__table__),
            ReferencedEntity(entity=inspect(Group), selectable=Group.__table__),
        ],
        None,
    )


def test_join_with_where(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(User).join(User.groups).join(UserGroup.group).where(Group.id == 1))
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(entity=inspect(User), selectable=User.__table__),
            ReferencedEntity(
                entity=inspect(UserGroup),
                selectable=UserGroup.__table__,
            ),
            ReferencedEntity(
                entity=inspect(Group),
                selectable=Group.__table__,
            ),
        ],
        ReferenceConditions(
            selectable=Group.__table__,
            conditions={"id": {"operator": eq, "value": 1}},
        ),
    )


def test_join_with_condition(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.scalar(select(User).join(User.groups).join(UserGroup.group.and_(Group.id == 1)))
    # Although the condition is on the join, treat it as without a condition for now
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(entity=inspect(User), selectable=User.__table__),
            ReferencedEntity(entity=inspect(UserGroup), selectable=UserGroup.__table__),
            ReferencedEntity(entity=inspect(Group), selectable=Group.__table__),
        ],
        ReferenceConditions(
            selectable=Group.__table__,
            conditions={"id": {"operator": eq, "value": 1}},
        ),
    )


def test_join_recursive(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.add(user_group)
        group = Group(name="Test Users 2")
        user_group.subgroups.append(group)
        session.add(group)
        session.commit()
        alias = aliased(Group)
        session.execute(select(Group).join(Group.subgroups.of_type(alias)))
    # Called when adding the subgroup
    auth_handler.before_select.assert_any_call(
        authorized_session,
        [ReferencedEntity(entity=inspect(Group), selectable=Group.__table__)],
        ReferenceConditions(
            selectable=Group.__table__,
            conditions={"parent_group_id": {"operator": eq, "value": 1}},
        ),
    )
    # Select itself
    auth_handler.before_select.assert_called_with(
        authorized_session,
        [
            ReferencedEntity(entity=inspect(Group), selectable=Group.__table__),
            ReferencedEntity(entity=inspect(Group), selectable=inspect(alias).selectable),
        ],
        None,
    )


def test_join_recursive_with_condition(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.add(user_group)
        group = Group(name="Test Users 2")
        user_group.subgroups.append(group)
        session.add(group)
        session.commit()
        alias = aliased(Group)
        session.execute(select(Group).join(Group.subgroups.of_type(alias)).where(alias.id == 2))
    # Called when adding the subgroup
    auth_handler.before_select.assert_any_call(
        authorized_session,
        [ReferencedEntity(entity=inspect(Group), selectable=Group.__table__)],
        ReferenceConditions(
            selectable=Group.__table__,
            conditions={"parent_group_id": {"operator": eq, "value": 1}},
        ),
    )
    # The select itself
    auth_handler.before_select.assert_called_with(
        authorized_session,
        [
            ReferencedEntity(entity=inspect(Group), selectable=Group.__table__),
            ReferencedEntity(
                entity=inspect(Group),
                selectable=inspect(alias).selectable,
            ),
        ],
        ReferenceConditions(
            selectable=inspect(alias).selectable,
            conditions={"id": {"operator": eq, "value": 2}},
        ),
    )


def test_join_selectinload(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(User).options(selectinload(User.groups).selectinload(UserGroup.group))).all()
    # First, the user table is queried
    auth_handler.before_select.assert_any_call(
        authorized_session,
        [ReferencedEntity(entity=inspect(User), selectable=User.__table__)],
        None,
    )
    # Then, a selectinload is performed on the user-groups
    auth_handler.before_select.assert_any_call(
        authorized_session,
        [
            ReferencedEntity(
                entity=inspect(UserGroup),
                selectable=UserGroup.__table__,
            )
        ],
        ReferenceConditions(
            selectable=UserGroup.__table__,
            conditions={"user_id": {"operator": in_op, "value": [1]}},
        ),
    )
    # Finally, a selectinload is performed on the groups as well
    auth_handler.before_select.assert_any_call(
        authorized_session,
        [
            ReferencedEntity(
                entity=inspect(Group),
                selectable=Group.__table__,
            )
        ],
        ReferenceConditions(
            selectable=Group.__table__,
            conditions={"id": {"operator": in_op, "value": [1]}},
        ),
    )


def test_join_joinedload(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(User).options(joinedload(User.groups).joinedload(UserGroup.group))).unique().all()
    # All should be queried at once
    auth_handler.before_select.assert_called_once()
    assert auth_handler.before_select.call_args_list[0].args[0] == authorized_session
    assert len(auth_handler.before_select.call_args_list[0].args[1]) == 3
    assert auth_handler.before_select.call_args_list[0].args[1][0] == ReferencedEntity(
        entity=inspect(User), selectable=User.__table__
    )
    # Joinedloads have anonymous aliases by default so it's hard to compare them
    assert auth_handler.before_select.call_args_list[0].args[1][1].entity == inspect(UserGroup)
    assert auth_handler.before_select.call_args_list[0].args[1][1].selectable.original == UserGroup.__table__
    assert auth_handler.before_select.call_args_list[0].args[1][2].entity == inspect(Group)
    assert auth_handler.before_select.call_args_list[0].args[1][2].selectable.original == Group.__table__
    assert auth_handler.before_select.call_args_list[0].args[2] is None


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


async def test_join_async(
    anyio_backend, async_engine, add_user_async, user_group_async, auth_handler, authorized_async_session
):
    async with authorized_async_session as session:
        await session.execute(select(User).join(User.groups).join(UserGroup.group))
    auth_handler.before_select.assert_called_once_with(
        authorized_async_session.sync_session,
        [
            ReferencedEntity(entity=inspect(User), selectable=User.__table__),
            ReferencedEntity(entity=inspect(UserGroup), selectable=UserGroup.__table__),
            ReferencedEntity(entity=inspect(Group), selectable=Group.__table__),
        ],
        None,
    )
