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
        return self.start < other.start

    def __gt__(self, other: Claim) -> bool:
        return self.start > other.start

    def __eq__(self, other: Claim) -> bool:
        return self.start == other.start and self.end == other.end

    def __le__(self, other: Claim) -> bool:
        return self.start <= other.start

    def __ge__(self, other: Claim) -> bool:
        return self.start >= other.start

    def __ne__(self, other: Claim) -> bool:
        return not self.__eq__(other)

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

    def __eq__(self, other: Maintenance) -> bool:
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
        start: Optional[datetime],
        end: Optional[datetime],
        end_user: Delegate | TenantOwner,
        resources: List[ResourceDefinition],
        hsn_only: bool = True,
    ):
        """
        Initialize the reservation.
        :param name: logical name
        :param start: start date, if empty find the best fit
        :param end: end date, if empty assume forever
        :param end_user: who is making the reservation for the resources
        :param resources: actual resources being reserved
        :param hsn_only: resources can only be used if directly connected to the high speed network
        """
        super().__init__(name, start, end)
        self.end_user = end_user
        self.resources = resources
        self.hsn_only = hsn_only

    def __eq__(self, other: Reservation) -> bool:
        return (
            super().__eq__(other)
            and self.end_user == other.end_user
            and self.resources == other.resources
        )

    def __hash__(self) -> int:
        return hash((self.name, self.start, self.end, self.end_user, self.resources))

    def extract(self) -> tuple[int, int, int, int]:
        """
        Extract the details of a claim.
        :return: tuple of compute CPU, RAM (in GB), accelerators and block storage (in TB) or None
        """
        claim_compute_cpu = sum(
            [c.cpu * c.amount for c in self.resources if isinstance(c, Compute)]
        )
        claim_compute_ram = sum(
            [c.ram * c.amount for c in self.resources if isinstance(c, Compute)]
        )
        claim_compute_accelerator = sum(
            [
                c.amount
                for c in self.resources
                if isinstance(c, Compute) and c.accelerator
            ]
        )
        claim_storage_block = sum(
            [
                s.amount
                for s in self.resources
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
