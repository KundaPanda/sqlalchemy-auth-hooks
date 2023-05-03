from sqlalchemy import inspect, select
from sqlalchemy.orm import aliased, joinedload, selectinload
from sqlalchemy.sql.operators import and_, eq, in_op

from sqlalchemy_auth_hooks.references import (
    CompositeCondition,
    LiteralExpression,
    ReferenceCondition,
    ReferencedEntity,
)
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
        ReferenceCondition(
            left=Group.__table__.c.id,
            operator=eq,
            right=UserGroup.__table__.c.group_id,
        ),
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
        CompositeCondition(
            operator=and_,
            conditions=[
                ReferenceCondition(
                    left=Group.__table__.c.id,
                    operator=eq,
                    right=UserGroup.__table__.c.group_id,
                ),
                ReferenceCondition(
                    left=Group.__table__.c.id,
                    operator=eq,
                    right=LiteralExpression(1),
                ),
            ],
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
        CompositeCondition(
            operator=and_,
            conditions=[
                ReferenceCondition(
                    left=Group.__table__.c.id,
                    operator=eq,
                    right=UserGroup.__table__.c.group_id,
                ),
                ReferenceCondition(
                    left=Group.__table__.c.id,
                    operator=eq,
                    right=LiteralExpression(1),
                ),
            ],
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
        ReferenceCondition(
            left=LiteralExpression(1),
            operator=eq,
            right=Group.__table__.c.parent_group_id,
        ),
    )
    # Select itself
    auth_handler.before_select.assert_called_with(
        authorized_session,
        [
            ReferencedEntity(entity=inspect(Group), selectable=Group.__table__),
            ReferencedEntity(entity=inspect(Group), selectable=inspect(alias).selectable),
        ],
        ReferenceCondition(
            left=Group.__table__.c.id,
            operator=eq,
            right=inspect(alias).selectable.c.parent_group_id,
        ),
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
        ReferenceCondition(
            left=LiteralExpression(1),
            operator=eq,
            right=Group.__table__.c.parent_group_id,
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
        CompositeCondition(
            operator=and_,
            conditions=[
                ReferenceCondition(
                    left=Group.__table__.c.id,
                    operator=eq,
                    right=inspect(alias).selectable.c.parent_group_id,
                ),
                ReferenceCondition(
                    left=inspect(alias).selectable.c.id,
                    operator=eq,
                    right=LiteralExpression(2),
                ),
            ],
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
        ReferenceCondition(
            left=UserGroup.__table__.c.user_id,
            operator=in_op,
            right=LiteralExpression([1]),
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
        ReferenceCondition(
            left=Group.__table__.c.id,
            operator=in_op,
            right=LiteralExpression([1]),
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
    assert isinstance(auth_handler.before_select.call_args_list[0].args[2], ReferenceCondition)
    assert auth_handler.before_select.call_args_list[0].args[2].left.name == "id"
    assert auth_handler.before_select.call_args_list[0].args[2].operator == eq
    assert auth_handler.before_select.call_args_list[0].args[2].right.name == "group_id"


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
        ReferenceCondition(
            left=Group.__table__.c.id,
            operator=eq,
            right=UserGroup.__table__.c.group_id,
        ),
    )
