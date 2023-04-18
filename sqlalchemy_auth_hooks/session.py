import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = structlog.get_logger()


class CheckedSession(Session):
    pass


class AuthorizedSession(CheckedSession):
    def __init__(self, *args, user: object, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user


class UnauthorizedSession(CheckedSession):
    pass


class CheckedAsyncSession(AsyncSession):
    pass


class AuthorizedAsyncSession(CheckedAsyncSession):
    def __init__(self, *args, user: object, **kwargs):
        kwargs["sync_session_class"] = AuthorizedSession
        kwargs["user"] = user
        super().__init__(*args, **kwargs)
        self.user = user


class UnauthorizedAsyncSession(CheckedAsyncSession):
    def __init__(self, *args, **kwargs):
        kwargs["sync_session_class"] = UnauthorizedSession
        super().__init__(*args, **kwargs)


def check_skip(session: Session) -> bool:
    if not isinstance(session, (CheckedSession, CheckedAsyncSession)):
        logger.warning("Please use AuthorizedSession or UnauthorizedSession for explicit authorization control!")
        logger.warning("Skipping authorization checks since session is not an instance of AuthorizedSession")
        return True
    return isinstance(session, (UnauthorizedSession, UnauthorizedAsyncSession))
