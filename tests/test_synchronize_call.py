import os
import time
from datetime import datetime

import pytest
from pytest_httpserver import HTTPServer

from horao.conceptual.support import Update
from horao.controllers.synchronization import SynchronizePeers
from horao.logical.infrastructure import LogicalInfrastructure
from horao.physical.computer import Server
from horao.physical.status import DeviceStatus
from tests.helpers import initialize_logical_infrastructure


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return "localhost", 9999


def test_changes_pass(httpserver: HTTPServer):
    httpserver.expect_request("/synchronize").respond_with_data("OK")
    os.environ["DEBUG"] = "True"
    os.environ["TELEMETRY"] = "OFF"
    os.environ["PEER_STRICT"] = "False"
    os.environ["PEERS"] = "http://localhost:9999"
    os.environ["PEER_SECRET"] = "secret"
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure(infrastructure={dc: [dcn]})
    SynchronizePeers(infrastructure)
    assert len(dc.changes) == 1
    dc[1][0].servers.append(
        Server("123", "foo", "42", 42, [], [], [], [], [], DeviceStatus.Up)
    )
    assert len(dc.changes) == 0
    dc[1][0].servers.append(
        Server("124", "foo", "43", 43, [], [], [], [], [], DeviceStatus.Up)
    )
    assert len(dc.changes) == 1
    httpserver.check_assertions()


def test_backpressure_timed():
    os.environ["DEBUG"] = "True"
    os.environ["TELEMETRY"] = "OFF"
    os.environ["PEER_STRICT"] = "False"
    os.environ["PEERS"] = "localhost"
    os.environ["PEER_SECRET"] = "secret"
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure(infrastructure={dc: [dcn]})
    sync_peers = SynchronizePeers(infrastructure, sync_delta=1)
    assert isinstance(
        sync_peers.synchronize([Update(b"1", 1.1, None, None, None, None)]), datetime
    )
    assert sync_peers.synchronize([Update(b"1", 1.1, None, None, None, None)]) is None
    time.sleep(1)
    assert isinstance(
        sync_peers.synchronize([Update(b"1", 1.1, None, None, None, None)]), datetime
    )


def test_backpressure_stacked():
    os.environ["DEBUG"] = "True"
    os.environ["TELEMETRY"] = "OFF"
    os.environ["PEER_STRICT"] = "False"
    os.environ["PEERS"] = "localhost"
    os.environ["PEER_SECRET"] = "secret"
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure(infrastructure={dc: [dcn]})
    sync_peers = SynchronizePeers(infrastructure, max_changes=2)
    assert isinstance(
        sync_peers.synchronize([Update(b"1", 1.1, None, None, None, None)]), datetime
    )
    assert sync_peers.synchronize([Update(b"1", 1.1, None, None, None, None)]) is None
    assert (
        sync_peers.synchronize(
            [
                Update(b"1", 1.1, None, None, None, None),
                Update(b"2", 1.1, None, None, None, None),
            ]
        )
        is None
    )
    assert isinstance(
        sync_peers.synchronize(
            [
                Update(b"1", 1.1, None, None, None, None),
                Update(b"2", 1.1, None, None, None, None),
                Update(b"3", 1.1, None, None, None, None),
            ]
        ),
        datetime,
    )
