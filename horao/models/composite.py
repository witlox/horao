# -*- coding: utf-8 -*-#
"""Composite hardware models, e.g. servers, blades, nodes, etc."""
from __future__ import annotations

import logging
from abc import ABC
from typing import List, Optional, TypeVar, Generic, Iterable

from horao.crdts import FractionallyIndexedArray
from horao.crdts.data_types import Nothing, String, Integer, Float
from horao.models.decorators import instrument_class_function
from horao.models.network import NIC, DeviceStatus
from horao.models.components import Accelerator, Hardware, CPU, RAM, Disk, HardwareList

_inject = {
    "String": String,
    "Integer": Integer,
    "Float": Float,
    "Nothing": Nothing,
    "NIC": NIC,
}


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
        self._log = logging.getLogger(__name__)
        self._serial_number = String(serial_number)
        self._name = String(name)
        self._model = String(model)
        self._number = Integer(number)
        self.cpus = HardwareList[CPU]().extend(cpus)
        self.rams = HardwareList[RAM]().extend(rams)
        self.nics = HardwareList[NIC](inject=_inject).extend(nics)
        self.disks = HardwareList[Disk]().extend(disks) if disks else Nothing()
        self.accelerator = (
            HardwareList[Accelerator].extend(accelerators)
            if accelerators
            else Nothing()
        )

    @property
    def serial_number(self) -> str:
        return self._serial_number.value

    @property
    def name(self) -> str:
        return self._name.value

    @property
    def model(self) -> str:
        return self._model.value

    @property
    def number(self) -> int:
        return self._number.value

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
        self._status = True if status == DeviceStatus.Up else False

    @property
    def status(self) -> DeviceStatus:
        return DeviceStatus.Up if self._status else DeviceStatus.Down


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
        self._status = True if status == DeviceStatus.Up else False

    @property
    def status(self) -> DeviceStatus:
        return DeviceStatus.Up if self._status else DeviceStatus.Down


class Node(Hardware):
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
        self._log = logging.getLogger(__name__)
        self.modules = HardwareList[Module]().extends(modules)
        self._status = True if status == DeviceStatus.Up else False

    @property
    def status(self) -> DeviceStatus:
        return DeviceStatus.Up if self._status else DeviceStatus.Down


class Blade(Hardware):
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
        self.nodes = HardwareList[Node]().extends(nodes)
        self._status = True if status == DeviceStatus.Up else False

    @property
    def status(self) -> DeviceStatus:
        return DeviceStatus.Up if self._status else DeviceStatus.Down


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
        self._log = logging.getLogger(__name__)
        self.servers = HardwareList[Server]().extend(servers) if servers else Nothing()
        self.blades = HardwareList[Blade]().extend(blades) if blades else Nothing()


T = TypeVar("T", bound=Computer)


class ComputerList(Generic[T]):
    """ComputerList behaves as a list of composed hardware instances"""

    def __init__(self, content: List[T] = None) -> None:
        self._log = logging.getLogger(__name__)
        self._computers = FractionallyIndexedArray()
        if content:
            self.extend(content)

    @instrument_class_function(name="append", level=logging.DEBUG)
    def append(self, item: T) -> T:
        """
        Append a computer instance to the list
        :param item: instance of Computer
        :return: None
        """
        if not isinstance(item, Computer):
            raise ValueError("Cannot append non-computer instance to ComputerList")
        clock_uuid, time_stamp, data = self._computers.put_first(item, item.name)
        self._log.debug(
            f"Added {item.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return item

    def clear(self) -> None:
        self._computers = FractionallyIndexedArray()

    def copy(self) -> ComputerList[T]:
        results = ComputerList()
        results.extend(self.iter())
        return results

    def count(self):
        return len(self._computers.read_full())

    def extend(self, other: Iterable[T]) -> ComputerList[T]:
        for item in other:
            self._computers.append(item, item.name)
        return self

    def index(self, item: T) -> Optional[T]:
        return next(
            iter([i for i, h in enumerate(self._computers.read_full()) if h == item]),
            None,
        )

    def insert(self, index: int, item: T) -> None:
        self._computers.put(item, item.name, Float(index))

    @instrument_class_function(name="pop", level=logging.DEBUG)
    def pop(self, index: int, default: T = None) -> Optional[T]:
        if index >= len(self._computers.read_full()):
            return default
        item = self._computers.read_full()[index]
        self._computers.delete(item, item.name)
        return item

    @instrument_class_function(name="remove", level=logging.DEBUG)
    def remove(self, item: T) -> None:
        """
        Remove a computer instance from the list
        :param item: instance of Hardware
        :return: None
        """
        fi_hardware = next(
            iter([h for h in self._computers.read_full() if h == item]), None
        )
        if not fi_hardware:
            self._log.error(f"{item.name} not found.")
        clock_uuid, time_stamp, data = self._computers.delete(fi_hardware, item.name)
        self._log.debug(
            f"Removed {item.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

    def reverse(self) -> HardwareList[T]:
        return self._computers.read_full()[::-1]

    def sort(self, item: T = None, reverse: bool = False) -> HardwareList[T]:
        """
        Not super valuable, orders by Computer Serial number
        :param item: key to sort by
        :param reverse: reverse the sort
        :return: HardwareList
        """
        return self._computers.read_full().sort(key=item, reverse=reverse)

    def __len__(self) -> int:
        return self.len()

    def __eq__(self, other: ComputerList[T]) -> bool:
        return self._computers.read_full() == other._computers.read_full()

    def __ne__(self, other: ComputerList[T]) -> bool:
        return self._computers.read_full() != other._computers.read_full()

    def __ge__(self, other: ComputerList[T]) -> bool:
        return self._computers.read_full() >= other._computers.read_full()

    def __gt__(self, other: ComputerList[T]) -> bool:
        return self._computers.read_full() > other._computers.read_full()

    def __le__(self, other: ComputerList[T]):
        return self._computers.read_full() <= other._computers.read_full()

    def __lt__(self, other: ComputerList[T]):
        return self._computers.read_full() < other._computers.read_full()

    def __contains__(self, item: T) -> bool:
        return item in self._computers.read_full()

    def __delitem__(self, item: T) -> None:
        if item not in self._computers.read_full():
            raise KeyError(f"{item} not found.")
        self.remove(item)

    def __getattr__(self, item: T) -> T:
        return self._computers.read_full()[item]

    def __getitem__(self, index: int) -> T:
        return self._computers.read_full()[index]

    def __setitem__(self, index: int, value: T) -> None:
        self._computers.put(value, value.name, Float(index))

    def __iter__(self) -> Iterable[T]:
        for item in self._computers.read_full():
            yield item

    def __next__(self) -> T:
        return next(self._computers.read_full())

    def __mul__(self, other: ComputerList[T]):
        raise TypeError("Cannot multiply ComputerList")

    def __add__(self, other: ComputerList[T]) -> ComputerList[T]:
        return self.extend(other.iter())

    def __sub__(self, other: ComputerList[T]) -> ComputerList[T]:
        for item in other.iter():
            self.remove(item)
        return self

    def __repr__(self) -> str:
        return f"ComputerList({self._computers.read_full()})"

    def __reversed__(self) -> HardwareList[T]:
        return self.reverse()

    def __sizeof__(self) -> int:
        return self.count()

    def __hash__(self):
        return hash(self._computers)
