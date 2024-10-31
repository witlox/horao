# -*- coding: utf-8 -*-#
import os
from datetime import datetime, timedelta

import pytest

from horao.conceptual.claim import Reservation
from horao.conceptual.osi_layers import LinkLayer
from horao.conceptual.tenant import Constraint, Tenant
from horao.logical.data_center import DataCenter, DataCenterNetwork
from horao.logical.infrastructure import Compute, LogicalInfrastructure
from horao.logical.scheduler import Scheduler, SchedulerFeature
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
            Port("1", "1", 1, "1", DeviceStatus.Up, False, 100),
            Port("1", "2", 2, "2", DeviceStatus.Up, False, 100),
        ],
        [],
    )
    server1 = Server(
        "1",
        "1",
        "server",
        1,
        [CPU("1", "1", 1, 2.4, 4, None), CPU("1", "1", 2, 2.4, 4, None)],
        [
            RAM("1", "1", 1, 16, None),
            RAM("1", "1", 2, 16, None),
            RAM("1", "1", 3, 16, None),
        ],
        [
            NIC(
                "1",
                "1",
                1,
                [Port("1", "1", 1, "1", DeviceStatus.Up, False, 100)],
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
        [CPU("1", "1", 1, 2.4, 4, None), CPU("1", "1", 2, 2.4, 4, None)],
        [
            RAM("1", "1", 1, 16, None),
            RAM("1", "1", 2, 16, None),
            RAM("1", "1", 3, 16, None),
        ],
        [
            NIC(
                "1",
                "1",
                1,
                [Port("1", "1", 1, "1", DeviceStatus.Up, False, 100)],
            )
        ],
        [],
        [],
        DeviceStatus.Up,
    )
    dc = DataCenter("dc", 1)
    dc[1] = [Cabinet("1", "1", "1", 1, [server1, server2], [], [core_switch])]
    dcn.add(core_switch)
    dcn.add(server1)
    dcn.add(server2)
    dcn.link(core_switch, server1)
    dcn.link(core_switch, server2)
    return dc, dcn


def test_basic_scheduler_infrastructure_limits():
    dc, dcn = initialize()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    assert infrastructure.limits() == (16, 96, 0, 0)


def test_extract_claim_details():
    start = datetime.now() + timedelta(hours=1)
    claim = Reservation(
        name="test",
        resources=[Compute(4, 4, False, 1)],
        start=start,
        end=datetime.now() + timedelta(days=1),
    )
    assert claim.extract() == (4, 4, 0, 0)


def test_tenant_constraints():
    constraint = Constraint([Compute(1, 1, False, 1)], [])
    tenant = Tenant("test1", "owner", constraints=[constraint])
    start = datetime.now() + timedelta(hours=1)
    claim = Reservation(
        name="test1-test",
        resources=[Compute(4, 4, False, 1)],
        start=start,
        end=datetime.now() + timedelta(days=1),
    )
    with pytest.raises(ValueError) as e:
        tenant.check_constraints(claim)
    assert "Claim exceeds tenant limits" in str(e.value)


def test_basic_scheduler_available_resources_can_be_claimed():
    dc, dcn = initialize()
    assert dcn.get_topology() == NetworkTopology.Tree
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = Scheduler(infrastructure)
    tenant = Tenant("test2", "owner")
    start = datetime.now() + timedelta(hours=1)
    claim = Reservation(
        name="test2-test",
        start=start,
        resources=[Compute(4, 4, False, 1)],
        end=datetime.now() + timedelta(days=1),
    )
    assert scheduler.schedule(claim, tenant) == start


def test_basic_scheduler_raises_error_filling_infrastructure():
    dc, dcn = initialize()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = Scheduler(infrastructure)
    tenant = Tenant("test3", "owner")
    start = datetime.now() + timedelta(hours=1)
    claim1 = Reservation(
        name="test3-test1",
        start=start,
        resources=[Compute(8, 4, False, 1)],
        end=datetime.now() + timedelta(days=1),
    )
    claim2 = Reservation(
        name="test3-test2",
        start=start,
        resources=[Compute(8, 8, False, 1)],
        end=datetime.now() + timedelta(days=1),
    )
    claim3 = Reservation(
        name="test3-test3",
        start=start,
        resources=[Compute(8, 16, False, 1)],
        end=datetime.now() + timedelta(days=1),
    )
    assert scheduler.schedule(claim1, tenant) == start
    assert scheduler.schedule(claim2, tenant) == start
    with pytest.raises(ValueError) as e:
        scheduler.schedule(claim3, tenant)
    assert "Claim exceeds compute CPU infrastructure limits" in str(e.value)


def test_claim_is_scheduled_when_enough_capacity_exists_in_time():
    dc, dcn = initialize()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    scheduler = Scheduler(infrastructure)
    tenant = Tenant("test4", "owner")
    start = datetime.now() + timedelta(hours=1)
    end = datetime.now() + timedelta(days=1)
    claim1 = Reservation(
        name="test4-test1",
        start=start,
        resources=[Compute(16, 4, False, 1)],
        end=end,
    )
    claim2 = Reservation(
        name="test4-test2",
        resources=[Compute(16, 24, False, 1)],
        end=end + timedelta(hours=1),
    )
    assert scheduler.schedule(claim1, tenant) == start
    with pytest.raises(ValueError) as e:
        scheduler.schedule(claim2, tenant)
    scheduler = Scheduler(infrastructure, [SchedulerFeature.DynamicStart])
    assert scheduler.schedule(claim2, tenant) >= end
