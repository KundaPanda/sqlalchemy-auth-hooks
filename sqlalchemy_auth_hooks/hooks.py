from sqlalchemy_auth_hooks.auth_handler import AuthHandler
from sqlalchemy_auth_hooks.core_hooks import register_core_hooks
from sqlalchemy_auth_hooks.orm_hooks import register_orm_hooks
from sqlalchemy_auth_hooks.post_auth_handler import PostAuthHandler


def register_hooks(auth_handler: AuthHandler, post_auth_handler: PostAuthHandler) -> None:
    """
    Register all hooks for SQLAlchemy events.
    """
    register_orm_hooks(auth_handler, post_auth_handler)
    register_core_hooks(auth_handler, post_auth_handler)
