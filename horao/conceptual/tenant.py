# -*- coding: utf-8 -*-#
"""Tenant as partitioning mechanism."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from horao.logical.resource import Compute, Storage
from horao.physical.storage import StorageType

from .claim import Reservation


@dataclass
class Tenant:
    name: str
    owner: str
    delegates: List[str] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)

    def __eq__(self, other: Tenant):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def check_constraints(self, reservation: Reservation) -> None:
        """
        Check if the claim exceeds tenant constraints
        :param reservation: the claim to check
        :return: None if the claim is within tenant constraints
        :raises ValueError: if the claim exceeds tenant constraints
        """
        (
            compute_cpu_claim,
            compute_ram_claim,
            accelerator_claim,
            block_storage_claim,
        ) = reservation.extract()
        for constraint in self.constraints:
            if (
                compute_cpu_claim > constraint.total_cpu_compute_limit()
                or compute_ram_claim > constraint.total_ram_compute_limit()
                or accelerator_claim > constraint.total_accelerator_compute_limit()
                or block_storage_claim > constraint.total_block_storage_limit()
            ):
                raise ValueError("Claim exceeds tenant limits")


@dataclass
class Constraint:
    compute_limits: List[Compute]
    storage_limits: List[Storage]

    def __eq__(self, other: Constraint):
        return (
            self.compute_limits == other.compute_limits
            and self.storage_limits == other.storage_limits
        )

    def __hash__(self):
        return hash((self.compute_limits, self.storage_limits))

    def total_block_storage_limit(self) -> int:
        return sum(
            [
                s.amount
                for s in self.storage_limits
                if s.storage_type == StorageType.Block
            ]
        )

    def total_object_storage_limit(self) -> int:
        return sum(
            [
                s.amount
                for s in self.storage_limits
                if s.storage_type == StorageType.Object
            ]
        )

    def total_cpu_compute_limit(self) -> int:
        return sum([c.cpu * c.amount for c in self.compute_limits])

    def total_ram_compute_limit(self) -> int:
        return sum([c.ram * c.amount for c in self.compute_limits])

    def total_accelerator_compute_limit(self) -> int:
        return sum([c.amount for c in self.compute_limits if c.accelerator])
