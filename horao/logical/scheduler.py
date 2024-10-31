# -*- coding: utf-8 -*-#
"""Scheduler logic for the High-Level Models used by HORAO"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import List, Optional

from horao.conceptual.claim import Reservation
from horao.conceptual.tenant import Tenant
from horao.logical.infrastructure import LogicalInfrastructure
from horao.logical.resource import Compute, Storage
from horao.physical.storage import StorageType


def dynamic_start_date(
    infrastructure: LogicalInfrastructure,
    reservation: Reservation,
) -> Reservation:
    """
    Calculate a dynamic start date for a reservation.
    :param infrastructure: logical infrastructure
    :param reservation: reservation to calculate start date for
    :return: reservation with start date
    """
    (
        total_infra_compute_cpu,
        total_infra_compute_ram,
        total_infra_compute_accelerator,
        total_infra_storage_block,
    ) = infrastructure.limits()
    (
        claim_compute_cpu,
        claim_compute_ram,
        claim_compute_accelerator,
        claim_storage_block,
    ) = reservation.extract()
    planning_window = timedelta(days=int(os.getenv("PLANNING_WINDOW", 31)))
    current_window = datetime.now()
    while current_window < datetime.now() + planning_window:
        other_claims_in_window = [
            c
            for cl in infrastructure.claims.values()
            for c in cl
            if (not c.start or not reservation.end or c.start < reservation.end)
            and (not c.end or c.end > current_window)
        ]
        if (
            claim_compute_cpu
            > total_infra_compute_cpu
            - sum(
                [
                    c.cpu * c.amount  # type: ignore
                    for cc in other_claims_in_window
                    for c in cc.resources  # type: ignore
                    if isinstance(c, Compute)
                ]
            )
            or (
                claim_compute_ram
                > total_infra_compute_ram
                - sum(
                    [
                        c.ram * c.amount  # type: ignore
                        for cc in other_claims_in_window
                        for c in cc.resources  # type: ignore
                        if isinstance(c, Compute)
                    ]
                )
            )
            or (
                claim_compute_accelerator
                > total_infra_compute_accelerator
                - sum(
                    [
                        c.amount  # type: ignore
                        for cc in other_claims_in_window
                        for c in cc.resources  # type: ignore
                        if isinstance(c, Compute) and c.accelerator
                    ]
                )
            )
            or (
                claim_storage_block
                > total_infra_storage_block
                - sum(
                    [
                        s.amount  # type: ignore
                        for sc in other_claims_in_window
                        for s in sc.resources  # type: ignore
                        if isinstance(s, Storage)
                        and s.storage_type is StorageType.Block
                    ]
                )
            )
        ):
            current_window += timedelta(hours=int(os.getenv("PLANNING_INTERVAL", 1)))
            continue
        reservation.start = current_window
        break
    return reservation


class SchedulerFeature(Enum):
    """Scheduler features that can be enabled or disabled."""

    DynamicStart = auto()
    DynamicResourcing = auto()


class Scheduler:
    """Scheduler that can either accept or reject a claim based on availability."""

    def __init__(
        self,
        infrastructure: LogicalInfrastructure,
        features: Optional[List[SchedulerFeature]] = None,
    ) -> None:
        """
        Initialize the basic scheduler.
        :param infrastructure: logical infrastructure to schedule on
        """
        self.infrastructure = infrastructure
        self.features = features or []

    def schedule(self, reservation: Reservation, tenant: Tenant) -> datetime:
        """
        Schedule a reservation for a tenant.
        Very basic logic, only checks if the reservation can be realised.
        Scanning for a start date happens with an hourly interval if start is not specified.
        We do not consider parallel reservations which can overlap in the future.
        todo: object storage not included yet
        :param reservation: reservation to schedule
        :param tenant: target tenant
        :return: datetime for when the claim is realised
        :raises ValueError: if the claim cannot be realised (reason in error message)
        """
        tenant.check_constraints(reservation)
        (
            total_infra_compute_cpu,
            total_infra_compute_ram,
            total_infra_compute_accelerator,
            total_infra_storage_block,
        ) = self.infrastructure.limits()
        (
            claim_compute_cpu,
            claim_compute_ram,
            claim_compute_accelerator,
            claim_storage_block,
        ) = reservation.extract()
        self.infrastructure.check_claim(reservation)
        if reservation.start:
            other_claims = [
                c
                for cl in self.infrastructure.claims.values()
                for c in cl
                if ((not c.start or not reservation.end) or c.start < reservation.end)
                and ((not c.end or not reservation.start) or c.end > reservation.start)
            ]
            if claim_compute_cpu > total_infra_compute_cpu - sum(
                [
                    c.cpu * c.amount  # type: ignore
                    for cc in other_claims
                    for c in cc.resources  # type: ignore
                    if isinstance(c, Compute)
                ]
            ):
                raise ValueError("Claim exceeds compute CPU infrastructure limits")
            if claim_compute_ram > total_infra_compute_ram - sum(
                [
                    c.ram * c.amount  # type: ignore
                    for cc in other_claims
                    for c in cc.resources  # type: ignore
                    if isinstance(c, Compute)
                ]
            ):
                raise ValueError("Claim exceeds compute RAM infrastructure limits")
            if claim_compute_accelerator > total_infra_compute_accelerator - sum(
                [
                    c.accelerator * c.amount  # type: ignore
                    for cc in other_claims
                    for c in cc.resources  # type: ignore
                    if isinstance(c, Compute)
                ]
            ):
                raise ValueError(
                    "Claim exceeds compute accelerator infrastructure limits"
                )
            if claim_storage_block > total_infra_storage_block - sum(
                [
                    s.amount  # type: ignore
                    for sc in other_claims
                    for s in sc.resources  # type: ignore
                    if isinstance(s, Storage)
                ]
            ):
                raise ValueError("Claim exceeds block storage infrastructure limits")
        else:
            if SchedulerFeature.DynamicStart in self.features:
                reservation = dynamic_start_date(self.infrastructure, reservation)
            else:
                raise ValueError(
                    "Claim cannot be realised, no start date specified and dynamic start not enabled"
                )
            reservation = dynamic_start_date(self.infrastructure, reservation)
        if not reservation.start:
            raise ValueError("Claim cannot be realised")
        if tenant not in self.infrastructure.claims.keys():
            self.infrastructure.claims[tenant] = []
        self.infrastructure.claims[tenant].append(reservation)
        return reservation.start
