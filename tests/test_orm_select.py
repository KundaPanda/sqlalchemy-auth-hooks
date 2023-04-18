from sqlalchemy import inspect, select
from sqlalchemy.sql.operators import and_, eq, or_, startswith_op

from sqlalchemy_auth_hooks.references import (
    CompositeConditions,
    ReferenceConditions,
    ReferencedEntity,
)
from tests.conftest import User, UserGroup


def test_simple_get(engine, add_user, auth_handler, authorized_session):
    with authorized_session as session:
        session.get(User, add_user.id)
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
        ReferenceConditions(selectable, {"id": {"operator": eq, "value": 1}}),
    )


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
        ReferenceConditions(selectable, {"id": {"operator": eq, "value": 1}}),
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
        ReferenceConditions(selectable, {"id": {"operator": eq, "value": 1}}),
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
        ReferenceConditions(selectable, {"id": {"operator": eq, "value": 1}}),
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
        CompositeConditions(
            operator=and_,
            conditions=[
                ReferenceConditions(selectable, {"user_id": {"operator": eq, "value": 1}}),
                ReferenceConditions(selectable, {"group_id": {"operator": eq, "value": 1}}),
            ],
        ),
    )


def test_select_get(engine, add_user, user_group, auth_handler, authorized_session):
    with authorized_session as session:
        session.get(UserGroup, (add_user.id, user_group.id))
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
        CompositeConditions(
            operator=and_,
            conditions=[
                ReferenceConditions(selectable, {"user_id": {"operator": eq, "value": 1}}),
                ReferenceConditions(selectable, {"group_id": {"operator": eq, "value": 1}}),
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
        CompositeConditions(
            operator=or_,
            conditions=[
                CompositeConditions(
                    operator=and_,
                    conditions=[
                        ReferenceConditions(
                            selectable=selectable,
                            conditions={"id": {"operator": eq, "value": 1}},
                        ),
                        ReferenceConditions(
                            selectable=selectable,
                            conditions={"name": {"operator": startswith_op, "value": "Jo"}},
                        ),
                    ],
                ),
                ReferenceConditions(
                    selectable=selectable,
                    conditions={"id": {"operator": eq, "value": 2}},
                ),
            ],
        ),
    )
