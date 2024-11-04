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


class Peer(BaseUser):
    def __init__(self, identity: str, token: str, payload, origin: str) -> None:
        self.id = identity
        self.token = token
        self.payload = payload
        self.origin = origin

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.origin

    @property
    def identity(self) -> str:
        return self.id

    def is_true(self) -> bool:
        """
        Check if the identity matches the origin.
        :return: bool
        """
        return self.identity == self.origin

    def __str__(self) -> str:
        return f"{self.origin} -> {self.identity}"


class MultiAuthBackend(AuthenticationBackend):
    logger = logging.getLogger(__name__)

    def digest_authentication(
        self, conn: HTTPConnection, token: str
    ) -> Union[None, Tuple[AuthCredentials, BaseUser]]:
        peer_match_source = False
        for peer in os.getenv("PEERS").split(","):  # type: ignore
            if peer in conn.client.host:
                self.logger.debug(f"Peer {peer} is trying to authenticate")
                peer_match_source = True
        if not peer_match_source and os.getenv("PEER_STRICT", "True") == "True":
            raise AuthenticationError(f"access not allowed for {conn.client.host}")
        payload = jwt.decode(token, os.getenv("PEER_SECRET"), algorithms=["HS256"])  # type: ignore
        self.logger.debug(f"valid token for {payload['peer']}")
        return AuthCredentials(["authenticated_peer"]), Peer(
            identity=payload["peer"],
            token=token,
            payload=payload,
            origin=conn.client.host,
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
            raise AuthenticationError(f"access not allowed for {conn.client.host}")