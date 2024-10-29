# -*- coding: utf-8 -*-#
"""Scheduler logic for the High-Level Models used by HORAO"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from horao.conceptual.tenant import Tenant
from horao.logical.claim import Claim, Reservation
from horao.logical.infrastructure import LogicalInfrastructure
from horao.logical.resource import Compute, Storage
from horao.physical.storage import StorageType


class BasicScheduler:
    """Very basic scheduler that can either accept or reject a claim based on availability."""

    def __init__(
        self,
        infrastructure: LogicalInfrastructure,
        planning_window: timedelta = timedelta(days=31),
    ) -> None:
        """
        Initialize the basic scheduler.
        :param infrastructure: logical infrastructure to schedule on
        :param planning_window: maximal planning window for reservations
        """
        self.infrastructure = infrastructure
        self.planning_window = planning_window
        self.claims: Dict[Tenant, List[Reservation]] = {}

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
        self._check_tenant_constraints(reservation, tenant)
        (
            total_infra_compute_cpu,
            total_infra_compute_ram,
            total_infra_compute_accelerator,
            total_infra_storage_block,
        ) = self._get_infrastructure_limits()
        (
            claim_compute_cpu,
            claim_compute_ram,
            claim_compute_accelerator,
            claim_storage_block,
        ) = self._extract_claim_details(reservation)
        self._check_infrastructure_limits(reservation)
        if reservation.start:
            other_claims = [
                c
                for cl in self.claims.values()
                for c in cl
                if (not c.start or c.start < reservation.end)
                and (not c.end or c.end > reservation.start)
            ]
            if claim_compute_cpu > total_infra_compute_cpu - sum(
                [
                    c.cpu * c.amount
                    for cc in other_claims
                    for c in cc.resources
                    if isinstance(c, Compute)
                ]
            ):
                raise ValueError("Claim exceeds compute CPU infrastructure limits")
            if claim_compute_ram > total_infra_compute_ram - sum(
                [
                    c.ram * c.amount
                    for cc in other_claims
                    for c in cc.resources
                    if isinstance(c, Compute)
                ]
            ):
                raise ValueError("Claim exceeds compute RAM infrastructure limits")
            if claim_compute_accelerator > total_infra_compute_accelerator - sum(
                [
                    c.accelerator * c.amount
                    for cc in other_claims
                    for c in cc.resources
                    if isinstance(c, Compute)
                ]
            ):
                raise ValueError(
                    "Claim exceeds compute accelerator infrastructure limits"
                )
            if claim_storage_block > total_infra_storage_block - sum(
                [
                    s.amount
                    for sc in other_claims
                    for s in sc.resources
                    if isinstance(s, Storage)
                ]
            ):
                raise ValueError("Claim exceeds block storage infrastructure limits")
        else:
            current_window = datetime.now()
            while current_window < datetime.now() + self.planning_window:
                other_claims_in_window = [
                    c
                    for cl in self.claims.values()
                    for c in cl
                    if (not c.start or not reservation.end or c.start < reservation.end)
                    and (not c.end or c.end > current_window)
                ]
                if (
                    claim_compute_cpu
                    > total_infra_compute_cpu
                    - sum(
                        [
                            c.cpu * c.amount
                            for cc in other_claims_in_window
                            for c in cc.resources
                            if isinstance(c, Compute)
                        ]
                    )
                    or (
                        claim_compute_ram
                        > total_infra_compute_ram
                        - sum(
                            [
                                c.ram * c.amount
                                for cc in other_claims_in_window
                                for c in cc.resources
                                if isinstance(c, Compute)
                            ]
                        )
                    )
                    or (
                        claim_compute_accelerator
                        > total_infra_compute_accelerator
                        - sum(
                            [
                                c.amount
                                for cc in other_claims_in_window
                                for c in cc.resources
                                if isinstance(c, Compute) and c.accelerator
                            ]
                        )
                    )
                    or (
                        claim_storage_block
                        > total_infra_storage_block
                        - sum(
                            [
                                s.amount
                                for sc in other_claims_in_window
                                for s in sc.resources
                                if isinstance(s, Storage)
                                and s.storage_type is StorageType.Block
                            ]
                        )
                    )
                ):
                    current_window += timedelta(hours=1)
                    continue
                reservation.start = current_window
                break
        if not reservation.start:
            raise ValueError("Claim cannot be realised")
        if tenant not in self.claims:
            self.claims[tenant] = []
        self.claims[tenant].append(reservation)
        return reservation.start

    @staticmethod
    def _extract_claim_details(
        reservation: Reservation,
    ) -> tuple[int, int, int, int]:
        """
        Extract the details of a claim.
        :param reservation: claim to extract details from
        :return: tuple of compute CPU, RAM (in GB), accelerators and block storage (in TB) or None
        """
        claim_compute_cpu = sum(
            [c.cpu * c.amount for c in reservation.resources if isinstance(c, Compute)]
        )
        claim_compute_ram = sum(
            [c.ram * c.amount for c in reservation.resources if isinstance(c, Compute)]
        )
        claim_compute_accelerator = sum(
            [
                c.amount
                for c in reservation.resources
                if isinstance(c, Compute) and c.accelerator
            ]
        )
        claim_storage_block = sum(
            [
                s.amount
                for s in reservation.resources
                if isinstance(s, Storage)
                if s.storage_type is StorageType.Block
            ]
        )
        return (
            claim_compute_cpu,
            claim_compute_ram,
            claim_compute_accelerator,
            claim_storage_block,
        )

    def _check_infrastructure_limits(self, reservation: Reservation) -> None:
        """
        Check if the reservation does not exceed the infrastructure limits.
        :param reservation: claim to check
        :return: None
        :raises ValueError: if the claim exceeds the infrastructure limits
        """
        (
            claim_compute_cpu,
            claim_compute_ram,
            claim_compute_accelerator,
            claim_storage_block,
        ) = self._extract_claim_details(reservation)
        (
            total_infra_compute_cpu,
            total_infra_compute_ram,
            total_infra_compute_accelerator,
            total_infra_storage_block,
        ) = self._get_infrastructure_limits()
        if claim_compute_cpu > total_infra_compute_cpu:
            raise ValueError("Claim exceeds compute CPU infrastructure limits")
        if claim_compute_ram > total_infra_compute_ram:
            raise ValueError("Claim exceeds compute RAM infrastructure limits")
        if claim_compute_accelerator > total_infra_compute_accelerator:
            raise ValueError("Claim exceeds compute accelerator infrastructure limits")
        if claim_storage_block > total_infra_storage_block:
            raise ValueError("Claim exceeds block storage infrastructure limits")
        if reservation.start and reservation.start < datetime.now():
            raise ValueError("Reservation cannot start in the past")
        if (
            reservation.start
            and reservation.end
            and reservation.end < reservation.start
        ):
            raise ValueError("Reservation cannot end before it starts")

    def _get_infrastructure_limits(self) -> tuple[int, int, int, int]:
        """
        Get the total infrastructure limits.
        :return: tuple of total compute CPUs, RAM (in GB), accelerators and block storage (in TB)
        """
        total_infra_compute_cpu = sum(
            [c.cpu * c.amount for c in self.infrastructure.total_compute()]
        )
        total_infra_compute_ram = sum(
            [c.ram * c.amount for c in self.infrastructure.total_compute()]
        )
        total_infra_compute_accelerator = sum(
            [c.amount for c in self.infrastructure.total_compute() if c.accelerator]
        )
        total_infra_storage_block = sum(
            [
                s.amount
                for s in self.infrastructure.total_storage()
                if s.storage_type is StorageType.Block
            ]
        )
        return (
            total_infra_compute_cpu,
            total_infra_compute_ram,
            total_infra_compute_accelerator,
            total_infra_storage_block,
        )

    def _check_tenant_constraints(
        self, reservation: Reservation, tenant: Tenant
    ) -> None:
        """
        Check if the claim exceeds tenant constraints
        :param reservation: the claim to check
        :param tenant: the tenant to validate
        :return: None
        :raises ValueError: if the claim exceeds tenant constraints
        """
        if tenant in self.infrastructure.constraints.keys():
            (
                compute_cpu_claim,
                compute_ram_claim,
                accelerator_claim,
                block_storage_claim,
            ) = self._extract_claim_details(reservation)
            if (
                compute_cpu_claim
                > self.infrastructure.constraints[tenant].total_cpu_compute_limit()
                or compute_ram_claim
                > self.infrastructure.constraints[tenant].total_ram_compute_limit()
                or accelerator_claim
                > self.infrastructure.constraints[
                    tenant
                ].total_accelerator_compute_limit()
                or block_storage_claim
                > self.infrastructure.constraints[tenant].total_block_storage_limit()
            ):
                raise ValueError("Claim exceeds tenant limits")
