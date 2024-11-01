# -*- coding: utf-8 -*-#
import os
from datetime import datetime, timedelta

import pytest

from horao.conceptual.claim import Reservation
from horao.conceptual.tenant import Constraint, Tenant
from horao.logical.infrastructure import Compute, LogicalInfrastructure
from horao.logical.scheduler import Scheduler, SchedulerFeature
from horao.physical.network import NetworkTopology
from tests.helpers import initialize_logical_infrastructure


def test_basic_scheduler_infrastructure_limits():
    dc, dcn = initialize_logical_infrastructure()
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
    dc, dcn = initialize_logical_infrastructure()
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
    dc, dcn = initialize_logical_infrastructure()
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
    dc, dcn = initialize_logical_infrastructure()
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
