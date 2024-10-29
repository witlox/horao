# -*- coding: utf-8 -*-#
"""Tenant as partitioning mechanism."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from horao.physical.storage import StorageType
from horao.logical.resource import Compute, Storage
from horao.rbac.roles import TenantOwner, Delegate


@dataclass
class Tenant:
    name: str
    owner: TenantOwner
    delegates: List[Delegate] = field(default_factory=list)
    shares: int = int(os.getenv("SHARES", 100))


@dataclass
class Constraint:
    target: Tenant
    compute_limits: List[Compute]
    storage_limits: List[Storage]

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
