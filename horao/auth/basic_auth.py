# -*- coding: utf-8 -*-#
"""Authorization module for the application.

Very basic auth module, DO NOT USE IN PRODUCTION!
Meant for development purpose only.
"""
import base64
import os

import binascii
from hashlib import sha256

from starlette.authentication import AuthenticationBackend, AuthenticationError, AuthCredentials, SimpleUser  # type: ignore
from starlette.requests import Request, HTTPException  # type: ignore
from starlette.responses import JSONResponse  # type: ignore


basic_auth_structure = {
    "netadm": {"password": "secret", "role": "network.admin"},
    "sysadm": {"password": "secret", "role": "system.admin"},
}


class BasicAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        if os.getenv("ENVIRONMENT") == "production":
            raise RuntimeError("Basic auth should not be used in production")
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
            raise HTTPException(
                status_code=401, detail=f"access not allowed for {username}"
            )
        return AuthCredentials(["authenticated"]), SimpleUser(username)


class PeerAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        if "Authorization" not in conn.headers:
            return
        auth = conn.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != "digest":
                return
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise AuthenticationError(f"Invalid digest credentials for peer ({exc})")
        if (
            not sha256(decoded.encode("utf-8")).hexdigest()
            == sha256(os.getenv("PEER_SECRET").encode("utf-8")).hexdigest()
        ):
            raise HTTPException(
                status_code=401, detail=f"access not allowed for {conn.client.host}"
            )
        return AuthCredentials(["peer"]), SimpleUser(conn.client.host)
