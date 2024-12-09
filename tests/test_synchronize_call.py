import os

import pytest

from horao.controllers.synchronization import SynchronizePeers
from horao.logical.infrastructure import LogicalInfrastructure
from horao.physical.computer import Server
from horao.physical.status import DeviceStatus
from tests.helpers import initialize_logical_infrastructure

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_backpressure_timed(mocker):
    os.environ["DEBUG"] = "True"
    os.environ["TELEMETRY"] = "OFF"
    os.environ["PEER_STRICT"] = "False"
    os.environ["PEERS"] = "localhost"
    os.environ["PEER_SECRET"] = "secret"
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure(infrastructure={dc: [dcn]})
    sync_peers = SynchronizePeers(infrastructure)
    spy = mocker.spy(sync_peers, "synchronize")
    assert dc.change_count() == 15
    assert spy.call_count == 0
    dc[1][0].servers.append(
        Server("123", "foo", "42", 42, [], [], [], [], [], DeviceStatus.Up)
    )
    assert dc.change_count() == 16
    assert spy.call_count == 1
