# -*- coding: utf-8 -*-#
"""Authorization for peers.

Digest authentication using pre-shared key.
"""
import base64
import binascii
import os
from hashlib import sha256

from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
)
from starlette.exceptions import HTTPException


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
