from sqlalchemy import inspect, literal, select
from sqlalchemy.sql.operators import and_, concat_op, eq, or_, startswith_op

from sqlalchemy_auth_hooks.references import (
    CompositeCondition,
    ColumnExpression,
    LiteralExpression,
    ReferenceCondition,
    ReferencedEntity,
)
from tests.core.conftest import User, UserGroup


def test_simple_select(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(User).filter_by(id=add_user.id))
    mapper = inspect(User)
    selectable = User.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        ReferenceCondition(
            left=selectable.c.id,
            operator=eq,
            right=LiteralExpression(add_user.id),
        ),
    )


def test_simple_select_where(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(User).where(User.id == add_user.id))
    mapper = inspect(User)
    selectable = User.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        ReferenceCondition(
            left=selectable.c.id,
            operator=eq,
            right=LiteralExpression(add_user.id),
        ),
    )


def test_simple_select_column_only(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(User.name).filter_by(id=add_user.id))
    mapper = inspect(User)
    selectable = User.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        ReferenceCondition(
            left=selectable.c.id,
            operator=eq,
            right=LiteralExpression(add_user.id),
        ),
    )


def test_select_multiple_pk(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(UserGroup).filter_by(user_id=add_user.id, group_id=user_group.id))
    mapper = inspect(UserGroup)
    selectable = UserGroup.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        CompositeCondition(
            operator=and_,
            conditions=[
                ReferenceCondition(
                    left=selectable.c.user_id,
                    operator=eq,
                    right=LiteralExpression(add_user.id),
                ),
                ReferenceCondition(
                    left=selectable.c.group_id,
                    operator=eq,
                    right=LiteralExpression(user_group.id),
                ),
            ],
        ),
    )


def test_select_multiple_conditions(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.scalars(select(User).where(or_(and_(User.id == add_user.id, User.name.startswith("Jo")), User.id == 2)))
    mapper = inspect(User)
    selectable = User.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        CompositeCondition(
            operator=or_,
            conditions=[
                CompositeCondition(
                    operator=and_,
                    conditions=[
                        ReferenceCondition(
                            left=selectable.c.id,
                            operator=eq,
                            right=LiteralExpression(add_user.id),
                        ),
                        ReferenceCondition(
                            left=selectable.c.name,
                            operator=startswith_op,
                            right=LiteralExpression("Jo"),
                        ),
                    ],
                ),
                ReferenceCondition(
                    left=selectable.c.id,
                    operator=eq,
                    right=LiteralExpression(2),
                ),
            ],
        ),
    )


def test_simple_select_func(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.execute(select(User.name + literal(" NAME")).where(User.name + literal(" NAME") == "John NAME"))
    mapper = inspect(User)
    selectable = User.__table__
    auth_handler.before_select.assert_called_once_with(
        authorized_session,
        [
            ReferencedEntity(
                entity=mapper,
                selectable=selectable,
            ),
        ],
        ReferenceCondition(
            left=ColumnExpression(left=selectable.c.name, operator=concat_op, right=LiteralExpression(" NAME")),
            operator=eq,
            right=LiteralExpression("John NAME"),
        ),
    )
