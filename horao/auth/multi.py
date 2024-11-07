# -*- coding: utf-8 -*-#
"""Authorization for peers.

Digest authentication using pre-shared key.
"""
import binascii
import logging
import os
from typing import Tuple, Union

import jwt
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
)
from starlette.requests import HTTPConnection

from horao.auth.roles import Peer


class MultiAuthBackend(AuthenticationBackend):
    logger = logging.getLogger(__name__)

    def digest_authentication(
        self, conn: HTTPConnection, token: str
    ) -> Union[None, Tuple[AuthCredentials, BaseUser]]:
        host = conn.client.host  # type: ignore
        peer_match_source = False
        for peer in os.getenv("PEERS").split(","):  # type: ignore
            if peer in host:
                self.logger.debug(f"Peer {peer} is trying to authenticate")
                peer_match_source = True
        if not peer_match_source and os.getenv("PEER_STRICT", "True") == "True":
            raise AuthenticationError(f"access not allowed for {host}")
        payload = jwt.decode(token, os.getenv("PEER_SECRET"), algorithms=["HS256"])  # type: ignore
        self.logger.debug(f"valid token for {payload['peer']}")
        return AuthCredentials(["authenticated"]), Peer(
            identity=payload["peer"],
            token=token,
            payload=payload,
            origin=host,
        )

    async def authenticate(
        self, conn: HTTPConnection
    ) -> Union[None, Tuple[AuthCredentials, BaseUser]]:
        if "Authorization" not in conn.headers:
            return None
        if "PEERS" not in os.environ:
            return None
        if "PEER_SECRET" not in os.environ:
            return None

        auth = conn.headers["Authorization"]
        try:
            scheme, token = auth.split()
            if scheme.lower() != "bearer":
                return None
            return self.digest_authentication(conn, token)
        except (
            ValueError,
            UnicodeDecodeError,
            jwt.InvalidTokenError,
            binascii.Error,
        ) as exc:
            self.logger.error(f"Invalid token for peer ({exc})")
            raise AuthenticationError(f"access not allowed for {conn.client.host}")  # type: ignore
