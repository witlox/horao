# -*- coding: utf-8 -*-#
"""Composite hardware models, e.g. servers, blades, nodes, etc."""
from __future__ import annotations

import logging
from abc import ABC
from typing import List, Optional, TypeVar, Generic, Iterable

from packify import pack, unpack

from horao.models.crdt import LastWriterWinsMap
from horao.models.decorators import instrument_class_function
from horao.models.network import NIC, DeviceStatus
from horao.models.components import Accelerator, Hardware, CPU, RAM, Disk, HardwareList


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
        return self.serial_number > other.serial_number

    def __lt__(self, other):
        return self.serial_number < other.serial_number

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


class ComputerList(Generic[T]):
    """ComputerList behaves as a list of composed hardware instances"""

    def __init__(
        self,
        content: List[T] = None,
        computers: LastWriterWinsMap = None,
        inject=None,
    ) -> None:
        """
        Initialize from an LastWriterWinsMap of item positions and a shared clock if supplied otherwise default.
        :param content: list of Hardware instances
        :param hardware: LastWriterWinsMap of hardware items
        :param inject: optional data to inject during unpacking
        """
        self.inject = {**globals()} if not inject else {**globals(), **inject}
        self.log = logging.getLogger(__name__)
        self.computers = LastWriterWinsMap() if computers is None else computers
        if content:
            self.extend(content)
        self.iterator = 0

    @instrument_class_function(name="append", level=logging.DEBUG)
    def append(self, item: T) -> T:
        """
        Append a computer instance to the list
        :param item: instance of Computer
        :return: None
        """
        self.computers.set(len(self.computers), item, hash(item))
        return item

    def clear(self) -> None:
        """
        Clear the list, not the history
        :return: None
        """
        # todo check history is consistent
        self.iterator = 0
        self.computers = LastWriterWinsMap()

    def copy(self) -> ComputerList[T]:
        results = ComputerList(inject=self.inject)
        results.extend(iter(self))
        return results

    def count(self):
        return len(self)

    def extend(self, other: Iterable[T]) -> ComputerList[T]:
        for item in other:
            self.computers.set(len(self), item, hash(item))
        return self

    def index(self, item: T) -> int:
        """
        Return the index of the computer instance
        :param item: instance to search for
        :return: int
        :raises ValueError: item not found
        """
        result = next(
            iter([i for i, h in self.computers.read(inject=self.inject) if h == item]),
            None,
        )
        if result is None:
            self.log.error(f"{item.name} not found.")
            raise ValueError(f"{item} not found.")
        return result

    def insert(self, index: int, item: T) -> None:
        self.computers.set(index, item, hash(item))

    @instrument_class_function(name="pop", level=logging.DEBUG)
    def pop(self, index: int, default: T = None) -> Optional[T]:
        if index >= len(self.computers.read(inject=self.inject)):
            self.log.debug(f"Index {index} out of bounds, returning default.")
            return default
        item = self.computers.read(inject=self.inject)[index]
        self.computers.unset(item, hash(item))
        return item

    @instrument_class_function(name="remove", level=logging.DEBUG)
    def remove(self, item: T) -> None:
        """
        Remove a computer instance from the list
        :param item: instance of Hardware
        :return: None
        :raises ValueError: item not found
        """
        local_item = next(
            iter([h for _, h in self.computers.read(inject=self.inject) if h == item]),
            None,
        )
        if not local_item:
            self.log.debug(f"{item.name} not found.")
            raise ValueError(f"{item} not found.")
        self.computers.unset(local_item, hash(item))

    def reverse(self) -> HardwareList[T]:
        """
        cannot reverse a list inplace in a CRDT
        :return: None
        :raises: NotImplementedError
        """
        raise NotImplementedError("Cannot reverse a list inplace in a CRDT")

    def sort(self, item: T = None, reverse: bool = False) -> HardwareList[T]:
        """
        cannot sort a list inplace in a CRDT
        :return: None
        :raises: NotImplementedError
        """
        raise NotImplementedError("Cannot sort a list inplace in a CRDT")

    def __len__(self) -> int:
        return len(self.computers.read(inject=self.inject))

    def __eq__(self, other: ComputerList[T]) -> bool:
        return self.computers.read(inject=self.inject) == other.computers.read(
            inject=self.inject
        )

    def __ne__(self, other: ComputerList[T]) -> bool:
        return self.computers.read(inject=self.inject) != other.computers.read(
            inject=self.inject
        )

    def __contains__(self, item: T) -> bool:
        return item in self.computers.read(inject=self.inject)

    def __delitem__(self, item: T) -> None:
        if item not in self.computers.read(inject=self.inject):
            raise KeyError(f"{item} not found.")
        self.remove(item)

    def __getitem__(self, index: int) -> T:
        return self.computers.read(inject=self.inject)[index]

    def __setitem__(self, index: int, value: T) -> None:
        self.computers.set(index, value, hash(value))

    def __iter__(self) -> Iterable[T]:
        for _, item in self.computers.read(inject=self.inject):
            yield item

    def __next__(self) -> T:
        if self.iterator >= len(self.computers.read(inject=self.inject)):
            self.iterator = 0
            raise StopIteration
        item = self.computers.read(inject=self.inject)[self.iterator]
        self.iterator += 1
        return item

    def __add__(self, other: ComputerList[T]) -> ComputerList[T]:
        return self.extend(iter(other))

    def __sub__(self, other: ComputerList[T]) -> ComputerList[T]:
        for item in iter(other):
            self.remove(item)
        return self

    def __repr__(self) -> str:
        return f"ComputerList({self.computers.read(inject=self.inject)})"

    def __reversed__(self) -> HardwareList[T]:
        return self.computers.read(inject=self.inject)[::-1]

    def __sizeof__(self) -> int:
        return self.count()

    def __hash__(self):
        return hash(self.computers)

    def pack(self) -> bytes:
        return self.computers.pack()

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> ComputerList[T]:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        computers = LastWriterWinsMap.unpack(data, inject=inject)
        return cls(computers=computers, inject=inject)
