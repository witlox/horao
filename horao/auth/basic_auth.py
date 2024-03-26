# -*- coding: utf-8 -*-#
"""Authorization module for the application.

Very basic auth module, DO NOT USE IN PRODUCTION!
Meant for development purpose only.
"""
import os
from typing import Optional, Dict

from horao.auth import UnauthenticatedError

basic_auth_structure = {
    "netadm": {"password": "secret", "role": "network.admin"},
    "sysadm": {"password": "secret", "role": "system.admin"},
}


def validate(username: str, password: str) -> Optional[Dict]:
    if os.getenv("ENVIRONMENT") != "production":
        raise RuntimeError("Basic auth should not be used in production")
    if username not in basic_auth_structure.keys():
        raise UnauthenticatedError(username)
    if basic_auth_structure[username] != password:
        raise UnauthenticatedError(username)
    return {"sub": username}
