# -*- coding: utf-8 -*-#
"""Basic Authorization for testing the application.

Very basic auth module, DO NOT USE IN PRODUCTION!
Meant for development purpose only.
"""
import base64
import binascii
import logging
from base64 import b64encode

from starlette.authentication import (  # type: ignore
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
)
from starlette.requests import HTTPException, Request  # type: ignore
from starlette.responses import JSONResponse  # type: ignore

from horao.auth.roles import Administrator, TenantController, User
from horao.conceptual.tenant import Tenant

basic_auth_structure = {
    "read_usr": {"password": "secret1", "role": User("read_usr")},
    "tenant": {
        "password": "secret2",
        "role": TenantController("tenant", [Tenant("test", "owner")]),
    },
    "admin": {"password": "secret3", "role": Administrator("admin")},
}


class BasicAuthBackend(AuthenticationBackend):
    logger = logging.getLogger(__name__)

    async def authenticate(self, conn):
        self.logger.warning("Basic auth should not be used in production!!!")
        if "Authorization" not in conn.headers:
            return
        auth = conn.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != "basic":
                return
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise AuthenticationError(f"Invalid basic auth credentials ({exc})")
        username, _, password = decoded.partition(":")
        if (
            username not in basic_auth_structure.keys()
            or basic_auth_structure[username]["password"] != password
        ):
            raise AuthenticationError(f"access not allowed for {username}")
        return (
            AuthCredentials(["authenticated"]),
            basic_auth_structure[username]["role"],
        )


def basic_auth(username, password) -> str:
    """
    This function returns a basic auth token for the given username and password
    :param username: user
    :param password: pass
    :return: token
    """
    token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"
