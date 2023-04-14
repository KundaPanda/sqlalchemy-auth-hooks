from sqlalchemy_auth_hooks.handler import SQLAlchemyAuthHandler
from sqlalchemy_auth_hooks.orm_hooks import _register_orm_hooks


def register_hooks(handler: SQLAlchemyAuthHandler):
    """
    Register all hooks for SQLAlchemy events.
    """
    _register_orm_hooks(handler)
