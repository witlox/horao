# -*- coding: utf-8 -*-#
import json
import os

import jwt
from starlette.testclient import TestClient

from horao import init
from horao.auth import BasicAuthBackend
from horao.auth.basic import basic_auth
from horao.logical.infrastructure import LogicalInfrastructure
from horao.persistance import HoraoEncoder
from tests.helpers import initialize_logical_infrastructure


def test_ping_service_unauthorized():
    os.environ["TELEMETRY"] = "OFF"
    ia = init(BasicAuthBackend())
    with TestClient(ia) as client:
        lg = client.get("/ping")
        assert 403 == lg.status_code


def test_ping_service_authorized():
    os.environ["TELEMETRY"] = "OFF"
    ia = init(BasicAuthBackend())
    with TestClient(ia) as client:
        lg = client.get(
            "/ping", headers={"Authorization": basic_auth("netadm", "secret")}
        )
        assert 200 == lg.status_code


def test_synchronize_simple_structure():
    os.environ["DEBUG"] = "True"
    os.environ["TELEMETRY"] = "OFF"
    os.environ["PEER_STRICT"] = "False"
    os.environ["PEERS"] = "1,2"
    os.environ["PEER_SECRET"] = "secret"
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    token = jwt.encode(dict(peer="1"), os.environ["PEER_SECRET"], algorithm="HS256")
    ia = init()
    with TestClient(ia) as client:
        lg = client.post("/synchronize")
        assert 403 == lg.status_code
        lg = client.post(
            "/synchronize",
            headers={"Authorization": f"Bearer {token}"},
            json=json.dumps(infrastructure, cls=HoraoEncoder),
        )
        assert 200 == lg.status_code
