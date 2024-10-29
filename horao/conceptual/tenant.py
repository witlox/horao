# -*- coding: utf-8 -*-#
"""Tenant as partitioning mechanism."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from horao.logical.resource import Compute, Storage
from horao.physical.storage import StorageType
from horao.rbac.roles import Delegate, TenantOwner


@dataclass
class Tenant:
    name: str
    owner: TenantOwner
    delegates: List[Delegate] = field(default_factory=list)
    shares: int = int(os.getenv("SHARES", 100))

    def __eq__(self, other: Tenant):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


@dataclass
class Constraint:
    target: Tenant
    compute_limits: List[Compute]
    storage_limits: List[Storage]

    def __eq__(self, other: Constraint):
        return (
            self.target == other.target
            and self.compute_limits == other.compute_limits
            and self.storage_limits == other.storage_limits
        )

    def __hash__(self):
        return hash((self.target, self.compute_limits, self.storage_limits))

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
