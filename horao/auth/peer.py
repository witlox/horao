# -*- coding: utf-8 -*-#
"""Authorization for peers.

Digest authentication using pre-shared key.
"""
import base64
import binascii
import logging
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
)


def encode(text: str, secret: str, salt: bytes) -> bytes:
    """
    This function returns a digest auth token for the given text and secret
    :param text: text
    :param secret: secret
    :param salt: salt
    :return: token
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))
    fernet = Fernet(key)
    enc_text = fernet.encrypt(text.encode("utf-8"))
    return enc_text


def decode(token: bytes, secret: str, salt: bytes) -> str:
    """
    This function returns a digest auth token for the given text and secret
    :param token: token
    :param secret: secret
    :param salt: salt
    :return: text
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))
    fernet = Fernet(key)
    return fernet.decrypt(token).decode("utf-8")


def generate_digest(username: str, password: str, secret: str, salt: bytes) -> bytes:
    """
    This function returns a digest auth token for the given username, password, secret and salt
    :param username: username
    :param password: password
    :param secret: secret
    :param salt: salt
    :return: bytes
    """
    return encode(f"{username}{password}", secret, salt)


def extract_username_password(token: bytes, secret: str, salt: bytes) -> (str, str):
    """
    This function returns the username and password from the token
    :param token: token
    :param secret: secret
    :param salt: salt
    :return: typle of username and password
    """
    token = decode(token, secret, salt)
    return (
        token[0 : len(token) - len(os.getenv("PEER_KEY"))],
        token[len(token) - len(os.getenv("PEER_KEY")) :],
    )


class PeerAuthBackend(AuthenticationBackend):
    logger = logging.getLogger(__name__)

    async def authenticate(self, conn):
        if "Authorization" not in conn.headers:
            return
        auth = conn.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != "digest":
                return

            peer_match_source = False
            for peer in os.getenv("PEERS").split(","):
                if peer in conn.client.host:
                    self.logger.debug(f"Peer {peer} is trying to authenticate")
                    peer_match_source = True
            if not peer_match_source and os.getenv("PEER_STRICT", "True") == "True":
                raise AuthenticationError(f"access not allowed for {conn.client.host}")
            username, password = extract_username_password(
                base64.b64decode(credentials),
                os.getenv("PEER_SECRET"),
                bytes.fromhex(os.getenv("PEER_SALT")),
            )
            for peer in os.getenv("PEERS").split(","):
                if peer == username and password == os.getenv("PEER_KEY"):
                    if not peer_match_source:
                        self.logger.warning(
                            f"Peer {peer} authenticated from different source {conn.client.host}"
                        )
                    return AuthCredentials(["peer"]), SimpleUser(peer)
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            self.logger.error(f"Invalid digest credentials for peer ({exc})")
            raise AuthenticationError(f"access not allowed for {conn.client.host}")
        raise AuthenticationError("access not allowed")
