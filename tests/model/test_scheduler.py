# -*- coding: utf-8 -*-#
import os
from datetime import datetime, timedelta

from horao.models import (
    NIC,
    Cabinet,
    DataCenter,
    DataCenterNetwork,
    DeviceStatus,
    LinkLayer,
    Port,
    Server,
    Switch,
    RAM,
    CPU,
)
from horao.models.logical import LogicalInfrastructure, Reservation, Tenant
from horao.models.network import NetworkTopology, NetworkType, SwitchType
from horao.models.scheduler import BasicScheduler, Compute
from horao.rbac.roles import TenantOwner

os.environ["ENVIRONMENT"] = "development"


def test_basic_scheduler_available_resources_can_be_claimed():
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    core_switch = Switch(
        "1",
        "1",
        "core",
        1,
        LinkLayer.Layer2,
        SwitchType.Core,
        DeviceStatus.Up,
        True,
        [
            Port("1", "1", "1", 1, "1", DeviceStatus.Up, False, 100),
            Port("1", "2", "1", 2, "2", DeviceStatus.Up, False, 100),
        ],
        [],
    )
    server1 = Server(
        "1",
        "1",
        "server",
        1,
        [CPU("1", "1", "1", 1, 2.4, 4, None), CPU("1", "1", "1", 2, 2.4, 4, None)],
        [
            RAM("1", "1", "1", 1, 16, None),
            RAM("1", "1", "1", 2, 16, None),
            RAM("1", "1", "1", 3, 16, None),
        ],
        [
            NIC(
                "1",
                "1",
                "1",
                1,
                [Port("1", "1", "1", 1, "1", DeviceStatus.Up, False, 100)],
            )
        ],
        [],
        [],
        DeviceStatus.Up,
    )
    server2 = Server(
        "2",
        "1",
        "server",
        2,
        [CPU("1", "1", "1", 1, 2.4, 4, None), CPU("1", "1", "1", 2, 2.4, 4, None)],
        [
            RAM("1", "1", "1", 1, 16, None),
            RAM("1", "1", "1", 2, 16, None),
            RAM("1", "1", "1", 3, 16, None),
        ],
        [
            NIC(
                "1",
                "1",
                "1",
                1,
                [Port("1", "1", "1", 1, "1", DeviceStatus.Up, False, 100)],
            )
        ],
        [],
        [],
        DeviceStatus.Up,
    )
    dc = DataCenter("dc", 1)
    dc[1] = [Cabinet("1", "1", "1", 1, [server1, server2], [], [core_switch])]
    dcn.add(core_switch)
    dcn.link(core_switch, server1.nics[0])
    dcn.link(core_switch, server2.nics[0])
    assert dcn.get_topology() == NetworkTopology.Tree
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = BasicScheduler(infrastructure)
    owner = TenantOwner()
    tenant = Tenant("test", owner)
    start = datetime.now()
    claim = Reservation(
        "test",
        start,
        datetime.now() + timedelta(days=1),
        owner,
        [Compute(4, 4, False, 1)],
        False,
    )
    assert scheduler.schedule(claim, tenant) == start
