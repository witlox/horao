# -*- coding: utf-8 -*-#
"""Tenant as partitioning mechanism."""
from __future__ import annotations

from typing import List, Optional

from horao.logical.resource import Compute, Storage
from horao.physical.storage import StorageType

from .claim import Reservation


class Tenant:
    def __init__(
        self,
        name: str,
        owner: str,
        delegates: Optional[List[str]] = None,
        constraints: Optional[List[Constraint]] = None,
    ):
        self.name = name
        self.owner = owner
        self.delegates = delegates if delegates is not None else []
        self.constraints = constraints if constraints is not None else []

    def __eq__(self, other):
        if not isinstance(other, Tenant):
            return False
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


class Constraint:

    def __init__(self, compute_limits: List[Compute], storage_limits: List[Storage]):
        self.compute_limits = compute_limits
        self.storage_limits = storage_limits

    def __eq__(self, other) -> bool:
        if not isinstance(other, Constraint):
            return False
        return (
            self.compute_limits == other.compute_limits
            and self.storage_limits == other.storage_limits
        )

    def __hash__(self) -> int:
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
