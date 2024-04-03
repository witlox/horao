# -*- coding: utf-8 -*-#
from base64 import b64encode

from starlette.testclient import TestClient

from horao import init_api
from tests import basic_auth


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
