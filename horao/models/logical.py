# -*- coding: utf-8 -*-#
"""Logical High-Level Models used by HORAO"""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Iterable, List, Tuple

from black import datetime

from horao.models import DataCenter, DataCenterNetwork
from horao.models.components import Hardware
from horao.models.composite import Computer
from horao.rbac.roles import (
    NetworkEngineer,
    PrincipalInvestigator,
    Researcher,
    SecurityEngineer,
    Student,
    SystemEngineer,
)


class Claim(ABC):
    """Base Class for Claims"""

    def __init__(self, name: str, start: datetime, end: datetime):
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
    """Represents a maintenance event in the data center."""

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


class Reservation(Claim):
    """Represents a logical reservation of resources."""

    def __init__(
        self,
        name: str,
        start: datetime,
        end: datetime,
        end_user: PrincipalInvestigator | Researcher | Student,
        resources: List[ResourceDefinition],
        hsn_only: bool = True,
    ):
        """
        Initialize the reservation.
        :param name: logical name
        :param start: start date
        :param end: end date
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


@dataclass
class LogicalInfrastructure:
    """
    Represents the logical infrastructure of a data center.
    Behaves as a dictionary of data center to list of data center networks.
    """

    infrastructure: Dict[DataCenter, List[DataCenterNetwork]] = field(
        default_factory=dict
    )

    def clear(self) -> None:
        self.infrastructure.clear()

    def copy(self) -> LogicalInfrastructure:
        return LogicalInfrastructure(
            {dc: networks.copy() for dc, networks in self.infrastructure.items()}
        )

    def has_key(self, k: DataCenter) -> bool:
        return k in self.infrastructure

    def update(self, key: DataCenter, value: List[DataCenterNetwork]) -> None:
        self.infrastructure[key] = value

    def keys(self) -> List[DataCenter]:
        return list(self.infrastructure.keys())

    def values(self) -> List[List[DataCenterNetwork]]:
        return list(self.infrastructure.values())

    def items(self) -> List[Tuple[DataCenter, List[DataCenterNetwork]]]:
        return list(self.infrastructure.items())

    def pop(self, key: DataCenter) -> List[DataCenterNetwork]:
        return self.infrastructure.pop(key)

    def __eq__(self, other: LogicalInfrastructure) -> bool:
        return self.infrastructure == other.infrastructure

    def __ne__(self, other: LogicalInfrastructure) -> bool:
        return not self == other

    def __setitem__(self, key, value) -> None:
        self.infrastructure[key] = value

    def __getitem__(self, key) -> List[DataCenterNetwork]:
        return self.infrastructure[key]

    def __delitem__(self, key) -> None:
        self.infrastructure.pop(key)

    def __repr__(self) -> str:
        return f"{self.infrastructure}"

    def __len__(self) -> int:
        return len(self.infrastructure)

    def __contains__(self, item) -> bool:
        return item in self.infrastructure

    def __iter__(self) -> Iterable[Tuple[DataCenter, List[DataCenterNetwork]]]:
        return iter(self.infrastructure.items())

    def __hash__(self) -> int:
        return hash(self.infrastructure)
