import os

import pytest

from horao.controllers.synchronization import SynchronizePeers
from horao.logical.infrastructure import LogicalInfrastructure
from horao.physical.network import Port
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
    assert dc.change_count() == 0
    assert spy.call_count == 0
    dc[1][0].switches[0].ports.append(
        Port("ser4", "lp", 3, "m4", DeviceStatus.Down, False, 100)
    )
    assert dc.change_count() == 1
    assert spy.call_count == 1
