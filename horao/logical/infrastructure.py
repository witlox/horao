# -*- coding: utf-8 -*-#
"""Logical High-Level Models used by HORAO"""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Tuple, Optional

from horao.conceptual.decorators import instrument_class_function
from horao.conceptual.tenant import Constraint, Tenant
from horao.logical.claim import Claim
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
        claims: Optional[List[Claim]] = None,
    ) -> None:
        """
        Initialize the logical infrastructure
        :param infrastructure: dictionary of data center to list of data center networks
        :param constraints: dictionary of tenant to constraints
        :param claims: list of claims
        """
        self.infrastructure = infrastructure or {}
        self.constraints = constraints or {}
        self.claims = claims or []

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
                for node in network.computers():
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
                for node in network.computers():
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
