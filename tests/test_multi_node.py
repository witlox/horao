import json
import os
from multiprocessing import Process
from typing import List

import jwt
import pytest
import uvicorn
from starlette.testclient import TestClient

from horao import init
from horao.logical.infrastructure import LogicalInfrastructure
from horao.physical.composite import Cabinet
from tests.helpers import initialize_logical_infrastructure

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def server1():
    proc = Process(target=uvicorn.run, args=("horao:init",), kwargs={"port": 8800})
    proc.start()
    yield
    proc.kill()


@pytest.fixture
def server2():
    proc = Process(target=uvicorn.run, args=("horao:init",), kwargs={"port": 8801})
    proc.start()
    yield
    proc.kill()


@pytest.mark.asyncio
async def test_backpressure_two_instances():
    os.environ["DEBUG"] = "True"
    os.environ["TELEMETRY"] = "OFF"
    os.environ["PEER_STRICT"] = "False"
    os.environ["PEERS"] = "localhost"
    os.environ["PEER_SECRET"] = "secret"
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    assert dc.summed_change_count() == 14
    # todo: logic needed for actual backpressure test
