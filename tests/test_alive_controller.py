# -*- coding: utf-8 -*-#
from base64 import b64encode

from starlette.testclient import TestClient

from horao import init_api


def basic_auth(username, password) -> str:
    """
    This function returns a basic auth token for the given username and password
    :param username: user
    :param password: pass
    :return: token
    """
    token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def test_ping_service_unauthorized():
    ia = init_api()
    with TestClient(ia) as client:
        lg = client.get("/ping")
        assert 403 == lg.status_code


def test_ping_service_authorized():
    ia = init_api()
    with TestClient(ia) as client:
        lg = client.get(
            "/ping", headers={"Authorization": basic_auth("netadm", "secret")}
        )
        assert 200 == lg.status_code
