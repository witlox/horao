# -*- coding: utf-8 -*-#
"""Authorization for peers.

Digest authentication using pre-shared key.
"""
import binascii
import logging
import os
from typing import Tuple, Union

import jwt
from authlib.integrations.starlette_client import OAuth  # type: ignore
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
)
from starlette.requests import HTTPConnection

from horao.auth.roles import Administrator, Peer, User


class MultiAuthBackend(AuthenticationBackend):
    logger = logging.getLogger(__name__)

    oauth_role_uri = os.getenv("OAUTH_ROLE_URI", "role")
    oauth_settings = {
        "name": os.getenv("OATH_NAME", "openidc"),
        "client_id": os.getenv("OAUTH_CLIENT_ID"),
        "client_secret": os.getenv("OAUTH_CLIENT_SECRET"),
        "server_metadata_url": os.getenv("OAUTH_SERVER_METADATA_URL", None),
        "api_base_url": os.getenv("OAUTH_API_BASE_URL", None),
        "authorize_url": os.getenv("OAUTH_AUTHORIZE_URL", None),
        "authorize_params": os.getenv("OAUTH_AUTHORIZE_PARAMS", None),
        "access_token_url": os.getenv("OAUTH_ACCESS_TOKEN_URL", None),
        "access_token_params": os.getenv("OAUTH_ACCESS_TOKEN_PARAMS", None),
        "request_token_url": os.getenv("OAUTH_REFRESH_TOKEN_URL", None),
        "request_token_params": os.getenv("OAUTH_REFRESH_TOKEN_PARAMS", None),
        "client_kwargs": os.getenv(
            "OAUTH_CLIENT_KWARGS", {"scope": f"openid email {oauth_role_uri}"}
        ),
    }

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

    async def oauth_authentication(
        self, conn: HTTPConnection
    ) -> Union[None, Tuple[AuthCredentials, BaseUser]]:
        oauth = OAuth()
        filtered_settings = {
            k: v for k, v in self.oauth_settings.items() if v is not None
        }
        client = oauth.register(filtered_settings)
        token = conn.headers["Authorization"]
        user = await client.authorize_access_token(token)
        if not user:
            raise AuthenticationError(f"Authentication failed for {conn.client.host}")  # type: ignore
        role = user.get(self.oauth_role_uri, "user")
        if not role or os.getenv("ADMINISTRATOR_ROLE", "administrator") not in role:
            return AuthCredentials(["authenticated"]), User(user["email"])
        return AuthCredentials(["authenticated"]), Administrator(user["email"])

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
        if "Peer" in conn.headers:
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
        else:
            return await self.oauth_authentication(conn)
