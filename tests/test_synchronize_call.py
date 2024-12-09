import os

import pytest

from horao.controllers.synchronization import SynchronizePeers
from horao.logical.infrastructure import LogicalInfrastructure
from horao.physical.computer import Server
from horao.physical.status import DeviceStatus
from tests.helpers import initialize_logical_infrastructure

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_backpressure_timed():
    os.environ["DEBUG"] = "True"
    os.environ["TELEMETRY"] = "OFF"
    os.environ["PEER_STRICT"] = "False"
    os.environ["PEERS"] = "localhost"
    os.environ["PEER_SECRET"] = "secret"
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure(infrastructure={dc: [dcn]})
    SynchronizePeers(infrastructure)
    assert len(dc.changes) == 1
    dc[1][0].servers.append(
        Server("123", "foo", "42", 42, [], [], [], [], [], DeviceStatus.Up)
    )
    assert len(dc.changes) == 4
