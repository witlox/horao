# -*- coding: utf-8 -*-#
"""Claims that can be made on the logical infrastructure."""
from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import List, Optional

from horao.logical.data_center import DataCenter, DataCenterNetwork
from horao.logical.resource import Compute, ResourceDefinition, Storage
from horao.physical.computer import Computer
from horao.physical.hardware import Hardware
from horao.physical.storage import StorageType
from horao.rbac.roles import (
    Delegate,
    NetworkEngineer,
    SecurityEngineer,
    SystemEngineer,
    TenantOwner,
)


class Claim(ABC):
    """Base Class for Claims"""

    def __init__(
        self,
        name: str,
        start: Optional[datetime],
        end: Optional[datetime],
    ):
        """
        Initialize the claim on a logical infrastructure for a given tenant.
        :param name: name of the claim
        :param start: start time
        :param end: end time
        """
        self.name = name
        self.start = start
        self.end = end

    def __lt__(self, other: Claim) -> bool:
        if not self.start and not other.start:
            return False
        if not self.start and other.start:
            return False
        if self.start and not other.start:
            return True
        return self.start < other.start  # type: ignore

    def __gt__(self, other: Claim) -> bool:
        return not self.__lt__(other)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Claim):
            return False
        return self.start == other.start and self.end == other.end

    def __le__(self, other: Claim) -> bool:
        if not self.start and not other.start:
            return True
        if not self.start and other.start:
            return True
        if self.start and not other.start:
            return False
        return self.start <= other.start  # type: ignore

    def __ge__(self, other: Claim) -> bool:
        return not self.__le__(other)

    def __hash__(self) -> int:
        return hash((self.name, self.start, self.end))

    def __repr__(self) -> str:
        return f"Claim(name={self.name}, start={self.start}, end={self.end})"


class Maintenance(Claim):
    """Represents a maintenance event in (a) data center(s)."""

    def __init__(
        self,
        name: str,
        start: datetime,
        end: datetime,
        reason: str,
        operator: SecurityEngineer | SystemEngineer | NetworkEngineer,
        target: List[DataCenter | DataCenterNetwork | Computer | Hardware],
    ):
        """
        Initialize the maintenance event.
        :param name: name of the event
        :param start: start time
        :param end: end time
        :param reason: explain the reason for the maintenance
        :param operator: type of operator requesting the maintenance
        :param target: list of targets for the maintenance
        """
        super().__init__(name, start, end)
        self.reason = reason
        self.operator = operator
        self.target = target

    def __eq__(self, other) -> bool:
        if not isinstance(other, Maintenance):
            return False
        return (
            super().__eq__(other)
            and self.reason == other.reason
            and self.operator == other.operator
            and self.target == other.target
        )

    def __hash__(self):
        return hash(
            (self.name, self.start, self.end, self.reason, self.operator, self.target)
        )


class Reservation(Claim):
    """Represents a logical reservation of resources."""

    def __init__(
        self,
        name: str,
        resources: List[ResourceDefinition],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        maximal_resources: Optional[List[ResourceDefinition]] = None,
        hsn_only: bool = True,
    ):
        """
        Initialize the reservation.
        :param name: logical name
        :param start: start date, if empty find the best fit
        :param end: end date, if empty assume forever
        :param resources: actual resources being reserved, or minimal if maximal_resources is set
        :param maximal_resources: maximal resources that can be used
        :param hsn_only: resources can only be used if directly connected to the high speed network
        """
        super().__init__(name, start, end)
        self.resources = resources
        self.maximal_resources = maximal_resources or []
        self.hsn_only = hsn_only

    def __eq__(self, other) -> bool:
        if not isinstance(other, Reservation):
            return False
        return (
            super().__eq__(other)
            and self.resources == other.resources
            and self.maximal_resources == other.maximal_resources
            and self.hsn_only == other.hsn_only
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.name,
                self.start,
                self.end,
                self.resources,
                self.maximal_resources,
                self.hsn_only,
            )
        )

    def extract(self, maximal: bool = False) -> tuple[int, int, int, int]:
        """
        Extract the details of a claim.
        :param maximal: extract maximal resources instead of minimal
        :return: tuple of compute CPU, RAM (in GB), accelerators and block storage (in TB) or None
        :raises ValueError: if maximal resources are requested but not defined
        """
        if maximal and not self.maximal_resources:
            raise ValueError("No maximal resources defined")
        resources = self.maximal_resources if maximal else self.resources
        claim_compute_cpu = sum(
            [c.cpu * c.amount for c in resources if isinstance(c, Compute)]
        )
        claim_compute_ram = sum(
            [c.ram * c.amount for c in resources if isinstance(c, Compute)]
        )
        claim_compute_accelerator = sum(
            [c.amount for c in resources if isinstance(c, Compute) and c.accelerator]
        )
        claim_storage_block = sum(
            [
                s.amount
                for s in resources
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
