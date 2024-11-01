# -*- coding: utf-8 -*-#
import base64
import json
import os

from starlette.testclient import TestClient

from horao import init_api
from horao.auth.basic_auth import basic_auth
from horao.auth.peer import encode, generate_digest
from horao.logical.infrastructure import LogicalInfrastructure
from horao.persistance import HoraoEncoder
from tests.helpers import initialize_logical_infrastructure


def test_ping_service_unauthorized():
    os.environ["TELEMETRY"] = "OFF"
    ia = init_api()
    with TestClient(ia) as client:
        lg = client.get("/ping")
        assert 403 == lg.status_code


def test_ping_service_authorized():
    os.environ["TELEMETRY"] = "OFF"
    ia = init_api()
    with TestClient(ia) as client:
        lg = client.get(
            "/ping", headers={"Authorization": basic_auth("netadm", "secret")}
        )
        assert 200 == lg.status_code


def test_synchronize_simple_structure():
    os.environ["TELEMETRY"] = "OFF"
    os.environ["PEER_STRICT"] = "False"
    os.environ["PEERS"] = "1,2"
    os.environ["PEER_KEY"] = "key"
    os.environ["PEER_SECRET"] = "secret"
    os.environ["PEER_SALT"] = os.urandom(16).hex()
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    token = base64.b64encode(
        generate_digest(
            "1",
            os.getenv("PEER_KEY"),
            os.getenv("PEER_SECRET"),
            bytes.fromhex(os.getenv("PEER_SALT")),
        )
    ).decode("ascii")
    ia = init_api()
    with TestClient(ia) as client:
        lg = client.post("/synchronize")
        assert 403 == lg.status_code
        lg = client.post(
            "/synchronize",
            headers={"Authorization": f"Digest {token}"},
            json={
                "LogicalInfrastructure": json.dumps(infrastructure, cls=HoraoEncoder)
            },
        )
        # todo fix this
        # assert 200 == lg.status_code
