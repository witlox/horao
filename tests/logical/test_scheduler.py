# -*- coding: utf-8 -*-#
import os
from datetime import datetime, timedelta

import pytest

from horao.conceptual.osi_layers import LinkLayer
from horao.conceptual.tenant import Constraint, Tenant
from horao.logical.claim import Reservation
from horao.logical.data_center import DataCenter, DataCenterNetwork
from horao.logical.infrastructure import Compute, LogicalInfrastructure
from horao.logical.scheduler import BasicScheduler
from horao.physical.component import CPU, RAM
from horao.physical.composite import Cabinet
from horao.physical.computer import Server
from horao.physical.network import (
    NIC,
    DeviceStatus,
    NetworkTopology,
    NetworkType,
    Port,
    Switch,
    SwitchType,
)
from horao.rbac.roles import TenantOwner

os.environ["ENVIRONMENT"] = "development"


def initialize():
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
    dcn.add(server1.nics[0], server1)
    dcn.add(server2.nics[0], server2)
    dcn.link(core_switch, server1.nics[0])
    dcn.link(core_switch, server2.nics[0])
    return dc, dcn


def test_basic_scheduler_infrastructure_limits():
    dc, dcn = initialize()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = BasicScheduler(infrastructure)
    assert scheduler._get_infrastructure_limits() == (8, 48, 0, 0)


def test_extract_claim_details():
    dc, dcn = initialize()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = BasicScheduler(infrastructure)
    owner = TenantOwner()
    start = datetime.now() + timedelta(hours=1)
    claim = Reservation(
        "test",
        start,
        datetime.now() + timedelta(days=1),
        owner,
        [Compute(4, 4, False, 1)],
        False,
    )
    assert scheduler._extract_claim_details(claim) == (4, 4, 0, 0)


def test_tenant_constraints():
    dc, dcn = initialize()
    owner = TenantOwner()
    tenant = Tenant("test1", owner)
    constraint = Constraint(tenant, [Compute(1, 1, False, 1)], [])
    infrastructure = LogicalInfrastructure(
        infrastructure={dc: [dcn]}, constraints={tenant: constraint}
    )
    scheduler = BasicScheduler(infrastructure)
    start = datetime.now() + timedelta(hours=1)
    claim = Reservation(
        "test1-test",
        start,
        datetime.now() + timedelta(days=1),
        owner,
        [Compute(4, 4, False, 1)],
        False,
    )
    with pytest.raises(ValueError) as e:
        scheduler._check_tenant_constraints(claim, tenant)
    assert "Claim exceeds tenant limits" in str(e.value)


def test_basic_scheduler_available_resources_can_be_claimed():
    dc, dcn = initialize()
    assert dcn.get_topology() == NetworkTopology.Tree
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = BasicScheduler(infrastructure)
    owner = TenantOwner()
    tenant = Tenant("test2", owner)
    start = datetime.now() + timedelta(hours=1)
    claim = Reservation(
        "test2-test",
        start,
        datetime.now() + timedelta(days=1),
        owner,
        [Compute(4, 4, False, 1)],
        False,
    )
    assert scheduler.schedule(claim, tenant) == start


def test_basic_scheduler_raises_error_filling_infrastructure():
    dc, dcn = initialize()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = BasicScheduler(infrastructure)
    owner = TenantOwner()
    tenant = Tenant("test3", owner)
    start = datetime.now() + timedelta(hours=1)
    claim1 = Reservation(
        "test3-test1",
        start,
        datetime.now() + timedelta(days=1),
        owner,
        [Compute(4, 4, False, 1)],
        False,
    )
    claim2 = Reservation(
        "test3-test2",
        start,
        datetime.now() + timedelta(days=1),
        owner,
        [Compute(4, 4, False, 1)],
        False,
    )
    claim3 = Reservation(
        "test3-test3",
        start,
        datetime.now() + timedelta(days=1),
        owner,
        [Compute(4, 4, False, 1)],
        False,
    )
    assert scheduler.schedule(claim1, tenant) == start
    assert scheduler.schedule(claim2, tenant) == start
    with pytest.raises(ValueError) as e:
        scheduler.schedule(claim3, tenant)
    assert "Claim exceeds compute CPU infrastructure limits" in str(e.value)


def test_claim_is_scheduled_when_enough_capacity_exists_in_time():
    dc, dcn = initialize()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = BasicScheduler(infrastructure)
    owner = TenantOwner()
    tenant = Tenant("test4", owner)
    start = datetime.now() + timedelta(hours=1)
    end = datetime.now() + timedelta(days=1)
    claim1 = Reservation(
        "test4-test1",
        start,
        end,
        owner,
        [Compute(8, 4, False, 1)],
        False,
    )
    claim2 = Reservation(
        "test4-test2",
        None,
        end + timedelta(hours=1),
        owner,
        [Compute(8, 4, False, 1)],
        False,
    )
    assert scheduler.schedule(claim1, tenant) == start
    assert scheduler.schedule(claim2, tenant) >= end
