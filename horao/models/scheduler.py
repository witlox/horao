# -*- coding: utf-8 -*-#
"""Scheduler logic for the High-Level Models used by HORAO"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict

from horao.models.logical import LogicalInfrastructure, Claim, Tenant, Reservation


@dataclass
class ResourceDefinition:
    """Base class for resource definitions."""

    amount: int = field(default=1)


class Compute(ResourceDefinition):
    """Represents a compute resource."""

    def __init__(
        self, cpu: int, ram: int, accelerator: bool, amount: int = None
    ) -> None:
        """
        Initialize the compute resource.
        :param cpu: amount of CPUs per node
        :param ram: amount of RAM in GB per node
        :param accelerator: requires an accelerator
        :param amount: total amount of nodes
        """
        super().__init__(amount)
        self.cpu = cpu
        self.ram = ram
        self.accelerator = accelerator

    def __eq__(self, other: Compute) -> bool:
        return (
            super().__eq__(other)
            and self.cpu == other.cpu
            and self.ram == other.ram
            and self.accelerator == other.accelerator
        )

    def __hash__(self):
        return hash((self.amount, self.cpu, self.ram, self.accelerator))


class StorageClass(Enum):
    """Available storage classes"""

    Hot = auto()
    Warm = auto()
    Cold = auto()


class StorageType(Enum):
    """Available storage types"""

    Block = auto()
    Object = auto()


class Storage(ResourceDefinition):
    """Represents a storage resource."""

    def __init__(
        self, capacity: int, storage_type: StorageType, storage_class: StorageClass
    ) -> None:
        """
        Initialize the storage resource.
        :param capacity: total capacity in TB
        :param storage_type: type of storage
        :param storage_class: class of storage
        """
        super().__init__(capacity)
        self.storage_type = storage_type
        self.storage_class = storage_class

    def __eq__(self, other: Storage) -> bool:
        return (
            super().__eq__(other)
            and self.storage_type == other.storage_type
            and self.storage_class == other.storage_class
        )

    def __hash__(self):
        return hash((self.amount, self.storage_type, self.storage_class))


class BasicScheduler:
    """Very basic scheduler that can either accept or reject a claim based on availability."""

    claims: Dict[Tenant, Claim] = {}

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
        if tenant in self.infrastructure.constraints.keys():
            compute_cpu_claim = sum(
                [c.cpu * c.amount for c in reservation.resources if c is Compute]
            )
            compute_ram_claim = sum(
                [c.ram * c.amount for c in reservation.resources if c is Compute]
            )
            accelerator_claim = sum(
                [
                    c.amount
                    for c in reservation.resources
                    if c is Compute and c.accelerator
                ]
            )
            block_storage_claim = sum(
                [
                    s.amount
                    for s in reservation.resources
                    if s is Storage and s.storage_type is StorageType.Block
                ]
            )
            if (
                compute_cpu_claim
                > self.infrastructure.constraints[tenant].total_cpu_compute_limit()
                and compute_ram_claim
                > self.infrastructure.constraints[tenant].total_ram_compute_limit()
                and accelerator_claim
                > self.infrastructure.constraints[
                    tenant
                ].total_accelerator_compute_limit()
                and block_storage_claim
                > self.infrastructure.constraints[tenant].total_block_storage_limit()
            ):
                raise ValueError("Claim exceeds tenant limits")
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
        claim_compute_cpu = sum(
            [c.cpu * c.amount for c in reservation.resources if c is Compute]
        )
        claim_compute_ram = sum(
            [c.ram * c.amount for c in reservation.resources if c is Compute]
        )
        claim_compute_accelerator = sum(
            [c.amount for c in reservation.resources if c is Compute and c.accelerator]
        )
        claim_storage_block = sum(
            [
                s.amount
                for s in reservation.resources
                if s is Storage
                if s.storage_type is StorageType.Block
            ]
        )
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
        if reservation.end and reservation.end < reservation.start:
            raise ValueError("Reservation cannot end before it starts")
        # get all reservations that overlap with the new reservation
        other_claims = [
            c
            for c in self.claims.values()
            if (not c.start or c.start < reservation.end)
            and (not c.end or c.end > reservation.start)
        ]
        if claim_compute_cpu > total_infra_compute_cpu - sum(
            [
                c.cpu * c.amount
                for c in self.infrastructure.total_compute()
                if c in other_claims
            ]
        ):
            raise ValueError("Claim exceeds compute CPU infrastructure limits")
        if claim_compute_ram > total_infra_compute_ram - sum(
            [
                c.ram * c.amount
                for c in self.infrastructure.total_compute()
                if c in other_claims
            ]
        ):
            raise ValueError("Claim exceeds compute RAM infrastructure limits")
        if claim_compute_accelerator > total_infra_compute_accelerator - sum(
            [
                c.amount
                for c in self.infrastructure.total_compute()
                if c in other_claims and c.accelerator
            ]
        ):
            raise ValueError("Claim exceeds compute accelerator infrastructure limits")
        if claim_storage_block > total_infra_storage_block - sum(
            [
                s.amount
                for s in self.infrastructure.total_storage()
                if s in other_claims and s.storage_type is StorageType.Block
            ]
        ):
            raise ValueError("Claim exceeds block storage infrastructure limits")
        if not reservation.start:
            current_window = datetime.now()
            while current_window < datetime.now() + self.planning_window:
                other_claims_in_window = [
                    c
                    for c in self.claims.values()
                    if (not c.start or not reservation.end or c.start < reservation.end)
                    and (not c.end or c.end > current_window)
                ]
                if (
                    claim_compute_cpu
                    > total_infra_compute_cpu
                    - sum(
                        [
                            c.cpu * c.amount
                            for c in self.infrastructure.total_compute()
                            if c in other_claims_in_window
                        ]
                    )
                    or (
                        claim_compute_ram
                        > total_infra_compute_ram
                        - sum(
                            [
                                c.ram * c.amount
                                for c in self.infrastructure.total_compute()
                                if c in other_claims_in_window
                            ]
                        )
                    )
                    or (
                        claim_compute_accelerator
                        > total_infra_compute_accelerator
                        - sum(
                            [
                                c.amount
                                for c in self.infrastructure.total_compute()
                                if c in other_claims_in_window and c.accelerator
                            ]
                        )
                    )
                    or (
                        claim_storage_block
                        > total_infra_storage_block
                        - sum(
                            [
                                s.amount
                                for s in self.infrastructure.total_storage()
                                if s in other_claims_in_window
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
        self.claims[tenant] = reservation
        return reservation.start
