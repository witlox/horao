# -*- coding: utf-8 -*-#
"""Logical High-Level Models used by HORAO"""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Tuple, Any

from horao.conceptual.claim import Claim, Reservation
from horao.conceptual.decorators import instrument_class_function
from horao.conceptual.tenant import Constraint, Tenant
from horao.logical.data_center import DataCenter, DataCenterNetwork
from horao.logical.resource import Compute, Storage
from horao.physical.composite import Blade
from horao.physical.computer import Server
from horao.physical.network import NetworkType
from horao.physical.storage import StorageClass, StorageType


class LogicalInfrastructure:
    """
    Represents the logical infrastructure of a data center.
    Behaves as a dictionary of data center to list of data center networks.
    """

    def __init__(
        self,
        infrastructure: Optional[Dict[DataCenter, List[DataCenterNetwork]]] = None,
        constraints: Optional[Dict[Tenant, Constraint]] = None,
        claims: Optional[Dict[Tenant, List[Claim]]] = None,
    ) -> None:
        """
        Initialize the logical infrastructure
        :param infrastructure: dictionary of data center to list of data center networks
        :param constraints: dictionary of tenant to constraints
        :param claims: list of claims
        """
        self.infrastructure = infrastructure or {}
        self.constraints = constraints or {}
        self.claims = claims or {}

    def changes(self) -> List[Any]:
        """
        Count the number of changes in the infrastructure.
        :return: number of changes
        """
        return [d.changes for d in self.infrastructure.keys()]

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

    def __eq__(self, other) -> bool:
        if not isinstance(other, LogicalInfrastructure):
            return False
        for k in self.infrastructure.keys():
            if k not in other.infrastructure:
                return False
            for l, r in zip(self.infrastructure[k], other.infrastructure[k]):
                if l != r:
                    return False
        return True

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

    def __contains__(self, item: DataCenter) -> bool:
        return item in self.infrastructure.keys()

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
                for node in network.computers():
                    if isinstance(node, Server):
                        compute.append(
                            Compute(
                                sum([n.cores for n in node.cpus]),  # type: ignore
                                sum([r.size_gb for r in node.rams]),  # type: ignore
                                len(node.accelerators) > 0,
                                1,
                            )
                        )
                    if isinstance(node, Blade):
                        for n in node.nodes:  # type: ignore
                            compute.append(
                                Compute(
                                    sum([c.cores for c in n.cpus]),  # type: ignore
                                    sum([r.size_gb for r in n.rams]),  # type: ignore
                                    len([m.accelerators for m in n.modules]) > 0,
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
                for node in network.computers():
                    if isinstance(node, Server):
                        storage.append(
                            Storage(
                                sum([d.size_gb for d in node.disks]),  # type: ignore
                                StorageType.Block,
                                StorageClass.Hot,
                            )
                        )
                    if isinstance(node, Blade):
                        for n in node.nodes:  # type: ignore
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

    def limits(self) -> tuple[int, int, int, int]:
        """
        Get the total infrastructure limits.
        :return: tuple of total compute CPUs, RAM (in GB), accelerators and block storage (in TB)
        """
        total_infra_compute_cpu = sum([c.cpu * c.amount for c in self.total_compute()])
        total_infra_compute_ram = sum([c.ram * c.amount for c in self.total_compute()])
        total_infra_compute_accelerator = sum(
            [c.amount for c in self.total_compute() if c.accelerator]
        )
        total_infra_storage_block = sum(
            [
                s.amount
                for s in self.total_storage()
                if s.storage_type is StorageType.Block
            ]
        )
        return (
            total_infra_compute_cpu,
            total_infra_compute_ram,
            total_infra_compute_accelerator,
            total_infra_storage_block,
        )

    def check_claim(self, reservation: Reservation) -> None:
        """
        Check if the claim exceeds infrastructure limits
        :param reservation: the claim to check
        :return: None
        :raises ValueError: if the claim exceeds infrastructure limits
        """
        (
            claim_compute_cpu,
            claim_compute_ram,
            claim_compute_accelerator,
            claim_storage_block,
        ) = reservation.extract()
        (
            total_infra_compute_cpu,
            total_infra_compute_ram,
            total_infra_compute_accelerator,
            total_infra_storage_block,
        ) = self.limits()
        if claim_compute_cpu > total_infra_compute_cpu:
            raise ValueError("Claim exceeds compute CPU infrastructure limits")
        if claim_compute_ram > total_infra_compute_ram:
            raise ValueError("Claim exceeds compute RAM infrastructure limits")
        if claim_compute_accelerator > total_infra_compute_accelerator:
            raise ValueError("Claim exceeds compute accelerator infrastructure limits")
        if claim_storage_block > total_infra_storage_block:
            raise ValueError("Claim exceeds block storage infrastructure limits")
        return None
