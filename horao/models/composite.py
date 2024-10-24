# -*- coding: utf-8 -*-#
"""Composite hardware models, e.g. servers, blades, nodes, etc."""
from __future__ import annotations

from abc import ABC
from typing import List, Optional, TypeVar

from packify import pack, unpack

from horao.models.components import Accelerator, Hardware, CPU, RAM, Disk, HardwareList
from horao.models.crdt import LastWriterWinsMap, CRDTList
from horao.models.network import NIC, DeviceStatus


class Computer(ABC):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpus: List[CPU],
        rams: List[RAM],
        nics: List[NIC],
        disks: Optional[List[Disk]],
        accelerators: Optional[List[Accelerator]],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.cpus = HardwareList[CPU](cpus)
        self.rams = HardwareList[RAM](rams)
        self.nics = HardwareList[NIC](nics)
        self.disks = HardwareList[Disk](disks) if disks else None
        self.accelerators = (
            HardwareList[Accelerator](accelerators) if accelerators else None
        )

    def __eq__(self, other):
        """
        Compare two computers, note that names are assumed to be unique
        :param other: instance of Computer
        :return: bool
        """
        if not isinstance(other, Hardware):
            return False
        if self.serial_number != other.serial_number:
            return False
        if not self.name == other.name:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return self.number > other.number

    def __lt__(self, other):
        return self.number < other.number

    def __hash__(self):
        return hash(self.serial_number)

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.cpus,
                self.rams,
                self.nics,
                self.disks,
                self.accelerators,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Computer:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        serial_number, name, model, number, cpus, rams, nics, disks, accelerators = (
            unpack(data, inject=inject)
        )
        return cls(
            serial_number, name, model, number, cpus, rams, nics, disks, accelerators
        )


class Server(Computer):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpus: List[CPU],
        rams: List[RAM],
        nics: List[NIC],
        disks: Optional[List[Disk]],
        accelerators: Optional[List[Accelerator]],
        status: DeviceStatus,
    ):
        super().__init__(
            serial_number, name, model, number, cpus, rams, nics, disks, accelerators
        )
        self.status = status

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.cpus,
                self.rams,
                self.nics,
                self.disks,
                self.accelerators,
                1 if self.status == DeviceStatus.Up else 0,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Server:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        (
            serial_number,
            name,
            model,
            number,
            cpus,
            rams,
            nics,
            disks,
            accelerators,
            status,
        ) = unpack(data, inject=inject)
        return cls(
            serial_number,
            name,
            model,
            number,
            cpus,
            rams,
            nics,
            disks,
            accelerators,
            DeviceStatus.Up if status == 1 else DeviceStatus.Down,
        )


class Module(Computer):
    """A module is a compute component that can be added to a node"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpus: List[CPU],
        rams: List[RAM],
        nics: List[NIC],
        disks: Optional[List[Disk]],
        accelerators: Optional[List[Accelerator]],
        status: DeviceStatus,
    ):
        super().__init__(
            serial_number, name, model, number, cpus, rams, nics, disks, accelerators
        )
        self.status = status

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.cpus,
                self.rams,
                self.nics,
                self.disks,
                self.accelerators,
                1 if self.status == DeviceStatus.Up else 0,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Module:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        (
            serial_number,
            name,
            model,
            number,
            cpus,
            rams,
            nics,
            disks,
            accelerators,
            status,
        ) = unpack(data, inject=inject)
        return cls(
            serial_number,
            name,
            model,
            number,
            cpus,
            rams,
            nics,
            disks,
            accelerators,
            DeviceStatus.Up if status == 1 else DeviceStatus.Down,
        )


class Node(Computer):
    """A node is a physical server that can host multiple modules"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        modules: List[Module],
        status: DeviceStatus,
    ):
        super().__init__(serial_number, name, model, number)
        self.modules = ComputerList[Module](modules)
        self.status = status

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.modules,
                1 if self.status == DeviceStatus.Up else 0,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Node:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        serial_number, name, model, number, modules, status = unpack(
            data, inject=inject
        )
        return cls(
            serial_number,
            name,
            model,
            number,
            modules,
            DeviceStatus.Up if status == 1 else DeviceStatus.Down,
        )


class Blade(Computer):
    """A blade is a physical server that can host multiple nodes"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        nodes: List[Node],
        status: DeviceStatus,
    ):
        super().__init__(serial_number, name, model, number)
        self.nodes = ComputerList[Node](nodes)
        self.status = status

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.nodes,
                1 if self.status == DeviceStatus.Up else 0,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Blade:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        serial_number, name, model, number, nodes, status = unpack(data, inject=inject)
        return cls(
            serial_number,
            name,
            model,
            number,
            nodes,
            DeviceStatus.Up if status == 1 else DeviceStatus.Down,
        )


class Chassis(Hardware):
    """A chassis hosts servers and/or blades"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        servers: Optional[List[Server]],
        blades: Optional[List[Blade]],
    ):
        super().__init__(serial_number, name, model, number)
        self.servers = ComputerList[Server](servers) if servers else None
        self.blades = ComputerList[Blade](blades) if blades else None


T = TypeVar("T", bound=Computer)


class ComputerList(CRDTList[T]):
    def __init__(
        self,
        computers: List[T] = None,
        items: LastWriterWinsMap = None,
        inject=None,
    ):
        super().__init__(computers, items, inject)
