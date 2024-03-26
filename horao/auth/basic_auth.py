# -*- coding: utf-8 -*-#
"""Authorization module for the application.

Very basic auth module, DO NOT USE IN PRODUCTION!
Meant for development purpose only.
"""
import os
import time
from typing import Optional, Dict

from jose import JWTError, jwt
from werkzeug.exceptions import Unauthorized

from horao.auth import UnauthenticatedError


basic_auth_structure = {
    "netadm": {"password": "secret", "role": "network.admin"},
    "sysadm": {"password": "secret", "role": "system.admin"},
}

JWT_ISSUER = "com.zalando.connexion"
JWT_SECRET = "change_this"
JWT_LIFETIME_SECONDS = 600
JWT_ALGORITHM = "HS256"


def login(username: str, password: str) -> str:
    if os.getenv("ENVIRONMENT") != "production":
        raise RuntimeError("Basic auth should not be used in production")
    if username not in basic_auth_structure.keys():
        raise Unauthorized(username)
    if basic_auth_structure[username] != password:
        raise Unauthorized(username)
    return generate_token(username)


def generate_token(user: str) -> str:
    timestamp = _current_timestamp()
    payload = {
        "iss": JWT_ISSUER,
        "iat": int(timestamp),
        "exp": int(timestamp + JWT_LIFETIME_SECONDS),
        "sub": str(user),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, str]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise Unauthorized from e


def get_secret(user: str, token_info: str) -> str:
    return """
    You are user_id {user}, decoded token claims: {token_info}.
    """.format(
        user=user, token_info=token_info
    )


def _current_timestamp() -> int:
    return int(time.time())
