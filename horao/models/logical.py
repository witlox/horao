# -*- coding: utf-8 -*-#
"""Logical High-Level Models used by HORAO"""
from __future__ import annotations

import logging
import os
from abc import ABC
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple, Optional

from black import datetime

from horao.models import DataCenter, DataCenterNetwork, NetworkType
from horao.models.components import Hardware
from horao.models.composite import Server, Blade, Computer
from horao.models.decorators import instrument_class_function
from horao.models.scheduler import (
    ResourceDefinition,
    Compute,
    Storage,
    StorageType,
    StorageClass,
)
from horao.rbac.roles import (
    NetworkEngineer,
    Delegate,
    TenantOwner,
    SecurityEngineer,
    SystemEngineer,
)


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


class Claim(ABC):
    """Base Class for Claims"""

    def __init__(self, name: str, start: Optional[datetime], end: Optional[datetime]):
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


@dataclass
class LogicalInfrastructure:
    """
    Represents the logical infrastructure of a data center.
    Behaves as a dictionary of data center to list of data center networks.
    """

    infrastructure: Dict[DataCenter, List[DataCenterNetwork]] = field(
        default_factory=dict
    )
    constraints: Dict[Tenant, Constraint] = field(default_factory=dict)
    claims: List[Claim] = field(default_factory=list)

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

    @instrument_class_function(name="total_compute", level=logging.DEBUG)
    def total_compute(self, hsn_only: bool = False) -> List[Compute]:
        """
        Calculate the total compute resources in the infrastructure.
        We currently assume that if a compute resource has disks, it is counted towards storage too.
        We also assume that there is no mixing of compute modules within a node within a blade.
        :param hsn_only: only count resources that are directly connected to the high speed network
        :return: list of compute resources
        """
        compute = []
        for dc, networks in self.infrastructure.items():
            data_networks = [n for n in networks if n.network_type == NetworkType.Data]
            if hsn_only:
                data_networks = [n for n in data_networks if n.hsn]
            for network in data_networks:
                for node in network.nodes():
                    if isinstance(node, Server):
                        compute.append(
                            Compute(
                                sum([n.cores for n in node.cpus]),
                                sum([r.size_gb for r in node.rams]),
                                len(node.accelerators) > 0,
                                1,
                            )
                        )
                    if isinstance(node, Blade):
                        for n in node.nodes():
                            compute.append(
                                Compute(
                                    sum([c.cores for c in n.cpus]),
                                    sum([r.size_gb for r in n.rams]),
                                    len(n.accelerators) > 0,
                                    len(n.modules),
                                )
                            )
        return compute

    @instrument_class_function(name="total_storage", level=logging.DEBUG)
    def total_storage(self, hsn_only: bool = False) -> List[Storage]:
        """
        Calculate the total storage resources in the infrastructure.
        We currently assume that if a compute resource has disks, it is counted towards storage too.
        :param hsn_only: only count resources that are directly connected to the high speed network
        :return: list of compute resources
        """
        storage = []
        for dc, networks in self.infrastructure.items():
            data_networks = [n for n in networks if n.network_type == NetworkType.Data]
            if hsn_only:
                data_networks = [n for n in data_networks if n.hsn]
            for network in data_networks:
                for node in network.nodes():
                    if isinstance(node, Server):
                        storage.append(
                            Storage(
                                sum([d.size_gb for d in node.disks]),
                                StorageType.Block,
                                StorageClass.Hot,
                            )
                        )
                    if isinstance(node, Blade):
                        for n in node.nodes():
                            storage.append(
                                Storage(
                                    sum(
                                        [
                                            sum([d.size_gb for d in m.disks])
                                            for m in n.modules
                                        ]
                                    ),
                                    StorageType.Block,
                                    StorageClass.Hot,
                                )
                            )
        return storage
