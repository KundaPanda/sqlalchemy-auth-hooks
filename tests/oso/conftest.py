from pathlib import Path

import pytest
from oso import Oso

from sqlalchemy_auth_hooks.hooks import register_hooks
from sqlalchemy_auth_hooks.oso.oso_handler import OsoHandler
from tests.conftest import User


@pytest.fixture(scope="session")
def oso(auth_user):
    oso = Oso()
    oso.register_class(User)
    oso.register_class(auth_user)
    base_path = Path(__file__).parent
    oso.load_files([base_path / "assets/authorization.polar"])
    return oso


@pytest.fixture
def oso_handler(oso):
    handler = OsoHandler(oso=oso, checked_permissions={User: "query"})
    register_hooks(handler)
    return handler
