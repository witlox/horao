# -*- coding: utf-8 -*-#
"""Datacenter hardware (compute & storage)

This module contains the definition of compute/storage equipment (hardware) and their properties.
We assume that 'faulty' equipment state is either up or down, it should be handled in a state machine, not here.
Also, we assume that these data structures are not very prone to change, given that this implies a manual activity.
"""
from __future__ import annotations

import logging
from abc import ABC
from typing import Generic, Iterable, List, Optional, TypeVar

from horao.crdts import FractionallyIndexedArray
from horao.crdts.data_types import Float, Integer, Nothing, String

from .decorators import instrument_class_function
from .network import NIC, Switch
from .status import DeviceStatus


class Hardware(ABC):
    def __init__(self, serial_number: str, name: str, model: str, number: int):
        self._serial_number = String(serial_number)
        self._name = String(name)
        self._model = String(model)
        self._number = Integer(number)

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

    def __eq__(self, other: Hardware) -> bool:
        """
        Compare two hardware instances, note that serial numbers are assumed to be unique
        :param other: instance of Hardware
        :return: bool
        """
        if not isinstance(other, Hardware):
            return False
        if self.serial_number != other.serial_number:
            return False
        if not (self.model == other.model and self.name == other.name):
            return False
        return True

    def __gt__(self, other: Hardware) -> bool:
        """
        Compare two hardware instances by serial number
        :param other: instance of Hardware
        :return: bool
        """
        return self.serial_number > other.serial_number

    def __lt__(self, other: Hardware) -> bool:
        """
        Compare two hardware instances by serial number
        :param other: instance of Hardware
        :return: bool
        """
        return self.serial_number < other.serial_number

    def __hash__(self) -> int:
        """
        Hash the hardware instance, note that number is not included in the hash
        :return: int
        """
        return hash((self.serial_number, self.name, self.model))


class RAM(Hardware):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        size_gb: int,
        speed_mhz: Optional[int],
    ):
        super().__init__(serial_number, name, model, number)
        self._size_gb = Integer(size_gb)
        self._speed_mhz = Integer(speed_mhz) if speed_mhz else Nothing()

    @property
    def size_gb(self) -> int:
        return self._size_gb.value

    @property
    def speed_mhz(self) -> Optional[int]:
        if isinstance(self._speed_mhz, Nothing):
            return None
        return self._speed_mhz.value


class CPU(Hardware):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        clock_speed: int,
        cores: int,
        features: Optional[str],
    ):
        super().__init__(serial_number, name, model, number)
        self._clock_speed = Integer(clock_speed)
        self._cores = Integer(cores)
        self._features = String(features) if features else Nothing()

    @property
    def clock_speed(self) -> int:
        return self._clock_speed.value

    @property
    def cores(self) -> int:
        return self._cores.value

    @property
    def features(self) -> Optional[str]:
        if isinstance(self._features, Nothing):
            return None
        return self._features.value


class Accelerator(Hardware):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        memory_gb: int,
        chip: Optional[str],
        clock_speed: Optional[int],
    ):
        super().__init__(serial_number, name, model, number)
        self._memory_gb = Integer(memory_gb)
        self._chip = String(chip) if chip else Nothing()
        self._clock_speed = Integer(clock_speed) if clock_speed else Nothing()

    @property
    def memory_gb(self) -> int:
        return self._memory_gb.value

    @property
    def chip(self) -> Optional[str]:
        if isinstance(self._chip, Nothing):
            return None
        return self._chip.value

    @property
    def clock_speed(self) -> Optional[int]:
        if isinstance(self._clock_speed, Nothing):
            return None
        return self._clock_speed.value


class Disk(Hardware):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        size_gb: int,
    ):
        super().__init__(serial_number, name, model, number)
        self._size_gb = Integer(size_gb)

    @property
    def size_gb(self) -> int:
        return self._size_gb.value


T = TypeVar("T", bound=Hardware)


class HardwareList(Generic[T]):

    def __init__(self) -> None:
        self._log = logging.getLogger(__name__)
        self._hardware = FractionallyIndexedArray()

    @instrument_class_function(name="append", level=logging.DEBUG)
    def append(self, item: T) -> T:
        """
        Append a hardware instance to the list
        :param item: instance of Hardware
        :return: None
        """
        if not isinstance(item, Hardware):
            raise ValueError("Cannot append non-hardware instance to HardwareList")
        clock_uuid, time_stamp, data = self._hardware.put_first(item, item.name)
        self._log.debug(
            f"Added {item.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return item

    def clear(self) -> None:
        self._hardware = FractionallyIndexedArray()

    def copy(self) -> HardwareList[T]:
        results = HardwareList()
        results.extend(self)
        return results

    def count(self):
        return len(self._hardware.read_full())

    def extend(self, other: Iterable[T]) -> None:
        for item in other:
            self._hardware.append(item, item.name)

    def index(self, item: T) -> Optional[T]:
        return next(
            iter([i for i, h in enumerate(self._hardware.read_full()) if h == item]),
            None,
        )

    def insert(self, index: int, item: T) -> None:
        self._hardware.put(item, item.name, Float(index))

    def pop(self, index: int) -> T:
        item = self._hardware.read_full()[index]
        self._hardware.delete(item, item.name)
        return item

    @instrument_class_function(name="remove", level=logging.DEBUG)
    def remove(self, item: T) -> None:
        """
        Remove a hardware instance from the list
        :param item: instance of Hardware
        :return: None
        """
        fi_hardware = next(
            iter([h for h in self._hardware.read_full() if h == item]), None
        )
        if not fi_hardware:
            self._log.error(f"{item.name} not found.")
        clock_uuid, time_stamp, data = self._hardware.delete(fi_hardware, item.name)
        self._log.debug(
            f"Removed {item.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

    def reverse(self) -> HardwareList[T]:
        return self._hardware.read_full()[::-1]

    def sort(self, item: T = None, reverse: bool = False) -> HardwareList[T]:
        """
        Not super valuable, orders by Hardware Serial number
        :param item: key to sort by
        :param reverse: reverse the sort
        :return: HardwareList
        """
        return self._hardware.read_full().sort(key=item, reverse=reverse)

    def __add__(self, item: T) -> T:
        return self.append(item)

    def __contains__(self, item: T) -> bool:
        return item in self._hardware.read_full()

    def __delitem__(self, item: T) -> None:
        if item not in self._hardware.read_full():
            raise KeyError(f"{item} not found.")
        self.remove(item)

    def __eq__(self, other: HardwareList[T]) -> bool:
        return self._hardware.read_full() == other._hardware.read_full()

    def __getattr__(self, item: T) -> T:
        return self._hardware.read_full()[item]

    def __getitem__(self, index: int) -> T:
        return self._hardware.read_full()[index]

    def __setitem__(self, index: int, value: T) -> None:
        self._hardware.put(value, value.name, Float(index))

    def __ge__(self, other: HardwareList[T]) -> bool:
        return self._hardware.read_full() >= other._hardware.read_full()

    def __gt__(self, other: HardwareList[T]) -> bool:
        return self._hardware.read_full() > other._hardware.read_full()

    def __le__(self, other: HardwareList[T]):
        return self._hardware.read_full() <= other._hardware.read_full()

    def __lt__(self, other: HardwareList[T]):
        return self._hardware.read_full() < other._hardware.read_full()

    def __iter__(self) -> Iterable[T]:
        for item in self._hardware.read_full():
            yield item

    def __len__(self) -> int:
        return self.len()

    def __mul__(self, other: HardwareList[T]):
        raise TypeError("Cannot multiply HardwareList")

    def __ne__(self, other: HardwareList[T]) -> bool:
        return self._hardware.read_full() != other._hardware.read_full()

    def __repr__(self) -> str:
        return f"HardwareList({self._hardware.read_full()})"

    def __reversed__(self) -> HardwareList[T]:
        return self.reverse()

    def __sizeof__(self) -> int:
        return self.count()

    def __hash__(self):
        return hash(self._hardware)


class Computer(ABC):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpus: HardwareList[CPU],
        rams: HardwareList[RAM],
        nics: HardwareList[NIC],
        disks: Optional[HardwareList[Disk]],
        accelerators: Optional[HardwareList[Accelerator]],
    ):
        self._log = logging.getLogger(__name__)
        self._serial_number = String(serial_number)
        self._name = String(name)
        self._model = String(model)
        self._number = Integer(number)
        self._cpu = FractionallyIndexedArray()
        for cpu in cpus:
            self._cpu.put_first(cpu, cpu.name)
        self._rams = FractionallyIndexedArray()
        for ram in rams:
            self._rams.put_first(ram, ram.name)
        self._nics = FractionallyIndexedArray()
        for nic in nics:
            self._nics.put_first(nic, nic.name)
        self._disks = FractionallyIndexedArray() if disks else Nothing()
        if not isinstance(self._disks, Nothing):
            for disk in disks:
                self._disks.put_first(disk, disk.name)
        self._accelerator = FractionallyIndexedArray() if accelerators else Nothing()
        if not isinstance(self._accelerator, Nothing):
            for accelerator in accelerators:
                self._accelerator.put_first(accelerator, accelerator.name)

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

    @property
    def cpus(self) -> List[CPU]:
        return [cpu.value for cpu in self._cpu.read_full()]

    @property
    def rams(self) -> List[RAM]:
        return [ram.value for ram in self._rams.read_full()]

    @property
    def nics(self) -> List[NIC]:
        return [nic.value for nic in self._nics.read_full()]

    @property
    def disks(self) -> Optional[List[Disk]]:
        if self._disks == Nothing():
            return None
        return [disk.value for disk in self._disks.read_full()]

    @instrument_class_function(name="add_disk", level=logging.DEBUG)
    def add_disk(self, disk: Disk) -> Disk:
        """
        Add a disk to the computer
        :param disk: disk to add
        :return: Disk
        :raises: ValueError if the computer doesn't support disks
        """
        if self._disks == Nothing():
            raise ValueError("Cannot add disk to computer without disk support")
        clock_uuid, time_stamp, data = self._disks.put_first(disk, disk.name)
        self._log.debug(
            f"Added disk {disk.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return disk

    @instrument_class_function(name="remove_disk", level=logging.DEBUG)
    def remove_disk(self, disk: Disk) -> None:
        """
        Remove a disk from the computer
        :param disk: disk to remove
        :return: None
        :raises: ValueError if the computer doesn't support disks
        """
        if self._disks == Nothing():
            raise ValueError("Cannot remove disk from computer without disk support")
        fi_disk = next(iter([d for d in self._disks.read_full() if d == disk]), None)
        if not fi_disk:
            self._log.error(f"Disk {disk.name} not found.")
        clock_uuid, time_stamp, data = self._disks.delete(fi_disk, disk.name)
        self._log.debug(
            f"Removed disk {disk.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

    @property
    def accelerators(self) -> Optional[List[Accelerator]]:
        if self._accelerator == Nothing():
            return None
        return [accelerator.value for accelerator in self._accelerator.read_full()]

    @instrument_class_function(name="add_accelerator", level=logging.DEBUG)
    def add_accelerator(self, accelerator: Accelerator) -> Accelerator:
        """
        Add an accelerator to the computer
        :param accelerator: accelerator to add
        :return: Accelerator
        :raises: ValueError if the computer doesn't support accelerators
        """
        if self._accelerator == Nothing():
            raise ValueError(
                "Cannot add accelerator to computer without accelerator support"
            )
        clock_uuid, time_stamp, data = self._accelerator.put_first(
            accelerator, accelerator.name
        )
        self._log.debug(
            f"Added accelerator {accelerator.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return accelerator

    @instrument_class_function(name="remove_accelerator", level=logging.DEBUG)
    def remove_accelerator(self, accelerator: Accelerator) -> None:
        """
        Remove an accelerator from the computer
        :param accelerator: accelerator to remove
        :return: None
        :raises: ValueError if the computer doesn't support accelerators
        """
        if self._accelerator == Nothing():
            raise ValueError(
                "Cannot remove accelerator from computer without accelerator support"
            )
        fi_accelerator = next(
            iter([a for a in self._accelerator.read_full() if a == accelerator]), None
        )
        if not fi_accelerator:
            self._log.error(f"Accelerator {accelerator.name} not found.")
        clock_uuid, time_stamp, data = self._accelerator.delete(
            fi_accelerator, accelerator.name
        )
        self._log.debug(
            f"Removed accelerator {accelerator.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
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
        self._modules = FractionallyIndexedArray()
        for module in modules:
            self._modules.put_first(module, module.name)
        self._status = True if status == DeviceStatus.Up else False

    @property
    def modules(self) -> List[Module]:
        return [module.value for module in self._modules.read_full()]

    @instrument_class_function(name="add_module", level=logging.DEBUG)
    def add_module(self, module: Module) -> Module:
        """
        Add a module to the node
        :param module: module to add
        :return: Module
        """
        clock_uuid, time_stamp, data = self._modules.put_first(module, module.name)
        self._log.debug(
            f"Added module {module.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return module

    @instrument_class_function(name="remove_module", level=logging.DEBUG)
    def remove_module(self, module: Module) -> None:
        """
        Remove a module from the node
        :param module: module to remove
        :return: None
        """
        fi_module = next(
            iter([m for m in self._modules.read_full() if m == module]), None
        )
        if not fi_module:
            self._log.error(f"Module {module.name} not found.")
        clock_uuid, time_stamp, data = self._modules.delete(fi_module, module.name)
        self._log.debug(
            f"Removed module {module.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

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
        self._log = logging.getLogger(__name__)
        self._nodes = FractionallyIndexedArray()
        for node in nodes:
            self._nodes.put_first(node, node.name)
        self._status = True if status == DeviceStatus.Up else False

    @property
    def nodes(self) -> List[Node]:
        return [node.value for node in self._nodes.read_full()]

    @instrument_class_function(name="add_node", level=logging.DEBUG)
    def add_node(self, node: Node) -> Node:
        """
        Add a node to the blade
        :param node: node to add
        :return: Node
        """
        clock_uuid, time_stamp, data = self._nodes.put_first(node, node.name)
        self._log.debug(
            f"Added node {node.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return node

    @instrument_class_function(name="remove_node", level=logging.DEBUG)
    def remove_node(self, node: Node) -> None:
        """
        Remove a node from the blade
        :param node: node to remove
        :return: None
        """
        fi_node = next(iter([n for n in self._nodes.read_full() if n == node]), None)
        if not fi_node:
            self._log.error(f"Node {node.name} not found.")
        clock_uuid, time_stamp, data = self._nodes.delete(fi_node, node.name)
        self._log.debug(
            f"Removed node {node.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

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
        self._servers = FractionallyIndexedArray() if servers else Nothing()
        if not isinstance(self._servers, Nothing):
            for server in servers:
                self._servers.put_first(server, server.name)
        self._blades = FractionallyIndexedArray() if blades else Nothing()
        if not isinstance(self._blades, Nothing):
            for blade in blades:
                self._blades.put_first(blade, blade.name)

    @property
    def servers(self) -> Optional[List[Server]]:
        if isinstance(self._servers, Nothing):
            return None
        return [server.value for server in self._servers.read_full()]

    @instrument_class_function(name="add_server", level=logging.DEBUG)
    def add_server(self, server: Server) -> Server:
        """
        Add a server to the chassis
        :param server: server to add
        :return: Server
        :raises: ValueError if the chassis doesn't support servers
        """
        if not self._servers:
            raise ValueError("Cannot add server to chassis without server support")
        clock_uuid, time_stamp, data = self._servers.put_first(server, server.name)
        self._log.debug(
            f"Added server {server.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return server

    @instrument_class_function(name="remove_server", level=logging.DEBUG)
    def remove_server(self, server: Server) -> None:
        """
        Remove a server from the chassis
        :param server: server to remove
        :return: None
        :raises: ValueError if the chassis doesn't support servers
        """
        if not self._servers:
            raise ValueError("Cannot remove server from chassis without server support")
        fi_server = next(
            iter([s for s in self._servers.read_full() if s == server]), None
        )
        if not fi_server:
            self._log.error(f"Server {server.name} not found.")
        clock_uuid, time_stamp, data = self._servers.delete(fi_server, server.name)
        self._log.debug(
            f"Removed server {server.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

    @property
    def blades(self) -> Optional[List[Blade]]:
        if isinstance(self._blades, Nothing):
            return None
        return [blade.value for blade in self._blades.read_full()]

    @instrument_class_function(name="add_blade", level=logging.DEBUG)
    def add_blade(self, blade: Blade) -> Blade:
        """
        Add a blade to the chassis
        :param blade: blade to add
        :return: Blade
        :raises: ValueError if the chassis doesn't support blades
        """
        if not self._blades:
            raise ValueError("Cannot add blade to chassis without blade support")
        clock_uuid, time_stamp, data = self._blades.put_first(blade, blade.name)
        self._log.debug(
            f"Added blade {blade.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return blade

    @instrument_class_function(name="remove_blade", level=logging.DEBUG)
    def remove_blade(self, blade: Blade) -> None:
        """
        Remove a blade from the chassis
        :param blade: blade to remove
        :return: None
        """
        if not self._blades:
            raise ValueError("Cannot remove blade from chassis without blade support")
        fi_blade = next(iter([b for b in self._blades.read_full() if b == blade]), None)
        if not fi_blade:
            self._log.error(f"Blade {blade.name} not found.")
        clock_uuid, time_stamp, data = self._blades.delete(fi_blade, blade.name)
        self._log.debug(
            f"Removed blade {blade.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )


class Cabinet(Hardware):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        servers: List[Server],
        chassis: List[Chassis],
        switches: List[Switch],
    ):
        super().__init__(serial_number, name, model, number)
        self._log = logging.getLogger(__name__)
        self._servers = FractionallyIndexedArray()
        for server in servers:
            self._servers.put_first(server, server.name)
        self._chassis = FractionallyIndexedArray()
        for chas in chassis:
            self._chassis.put_first(chas, chas.name)
        self._switches = FractionallyIndexedArray()
        for switch in switches:
            self._switches.put_first(switch, switch.name)

    @property
    def servers(self) -> List[Server]:
        return [server.value for server in self._servers.read_full()]

    @instrument_class_function(name="add_server", level=logging.DEBUG)
    def add_server(self, server: Server) -> Server:
        clock_uuid, time_stamp, data = self._servers.put_first(server, server.name)
        self._log.debug(
            f"Added server {server.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return server

    @instrument_class_function(name="remove_server", level=logging.DEBUG)
    def remove_server(self, server: Server) -> None:
        fi_server = next(
            iter([s for s in self._servers.read_full() if s == server]), None
        )
        if not fi_server:
            self._log.error(f"Server {server.name} not found.")
        clock_uuid, time_stamp, data = self._servers.delete(fi_server, server.name)
        self._log.debug(
            f"Removed server {server.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

    @property
    def chassis(self) -> List[Chassis]:
        return [c.value for c in self._chassis.read_full()]

    @instrument_class_function(name="add_chassis", level=logging.DEBUG)
    def add_chassis(self, chassis: Chassis) -> Chassis:
        clock_uuid, time_stamp, data = self._chassis.put_first(chassis, chassis.name)
        self._log.debug(
            f"Added chassis {chassis.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return chassis

    @instrument_class_function(name="remove_chassis", level=logging.DEBUG)
    def remove_chassis(self, chassis: Chassis) -> None:
        fi_chassis = next(
            iter([c for c in self._chassis.read_full() if c == chassis]), None
        )
        if not fi_chassis:
            self._log.error(f"Chassis {chassis.name} not found.")
        clock_uuid, time_stamp, data = self._chassis.delete(fi_chassis, chassis.name)
        self._log.debug(
            f"Removed chassis {chassis.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

    @property
    def switches(self) -> List[Switch]:
        return [switch.value for switch in self._switches.read_full()]

    @instrument_class_function(name="add_switch", level=logging.DEBUG)
    def add_switch(self, switch: Switch) -> Switch:
        clock_uuid, time_stamp, data = self._switches.put_first(switch, switch.name)
        self._log.debug(
            f"Added switch {switch.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return switch

    @instrument_class_function(name="remove_switch", level=logging.DEBUG)
    def remove_switch(self, switch: Switch) -> None:
        fi_switch = next(
            iter([s for s in self._switches.read_full() if s == switch]), None
        )
        if not fi_switch:
            self._log.error(f"Switch {switch.name} not found.")
        clock_uuid, time_stamp, data = self._switches.delete(fi_switch, switch.name)
        self._log.debug(
            f"Removed switch {switch.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )


class Row:
    """A row is a collection of cabinets (physical row in a DC)"""

    def __init__(self, name: str, number: int, cabinets: List[Cabinet]):
        self._log = logging.getLogger(__name__)
        self._name = String(name)
        self._number = Integer(number)
        self._cabinets = FractionallyIndexedArray()
        for cabinet in cabinets:
            self._cabinets.put_first(cabinet, cabinet.name)

    @property
    def name(self) -> str:
        return self._name.value

    @property
    def number(self) -> int:
        return self._number.value

    @property
    def cabinets(self) -> List[Cabinet]:
        return [cabinet.value for cabinet in self._cabinets.read_full()]

    @instrument_class_function(name="add_cabinet", level=logging.DEBUG)
    def add_cabinet(self, cabinet: Cabinet) -> Cabinet:
        clock_uuid, time_stamp, data = self._cabinets.put_first(cabinet, cabinet.name)
        self._log.debug(
            f"Added cabinet {cabinet.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return cabinet

    @instrument_class_function(name="remove_cabinet", level=logging.DEBUG)
    def remove_cabinet(self, cabinet: Cabinet) -> None:
        fi_cabinet = next(
            iter([c for c in self._cabinets.read_full() if c == cabinet]), None
        )
        if not fi_cabinet:
            self._log.error(f"Cabinet {cabinet.name} not found.")
        clock_uuid, time_stamp, data = self._cabinets.delete(fi_cabinet, cabinet.name)
        self._log.debug(
            f"Removed cabinet {cabinet.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )


class DataCenter:
    def __init__(self, name: str, number: int, rows: List[Row]):
        self._log = logging.getLogger(__name__)
        self._name = String(name)
        self._number = number
        self._rows = FractionallyIndexedArray()
        for row in rows:
            self._rows.put_first(row, row.name)

    @property
    def name(self) -> str:
        return self._name.value

    @property
    def number(self) -> int:
        return self._number

    @property
    def rows(self) -> List[Row]:
        return [row.value for row in self._rows.read_full()]

    @instrument_class_function(name="add_row", level=logging.DEBUG)
    def add_row(self, row: Row) -> Row:
        clock_uuid, time_stamp, data = self._rows.put_first(row, row.name)
        self._log.debug(
            f"Added row {row.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return row

    @instrument_class_function(name="remove_row", level=logging.DEBUG)
    def remove_row(self, row: Row) -> None:
        fi_row = next(iter([r for r in self._rows.read_full() if r == row]), None)
        if not fi_row:
            self._log.error(f"Row {row.name} not found.")
        clock_uuid, time_stamp, data = self._rows.delete(fi_row, row.name)
        self._log.debug(
            f"Removed row {row.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )

    @staticmethod
    def move_server(server: Server, from_cabinet: Cabinet, to_cabinet: Cabinet) -> None:
        """
        Move a server from one cabinet to another
        :param server: server to move
        :param from_cabinet: from
        :param to_cabinet: to
        :return: None
        """
        from_cabinet.remove_server(server)
        to_cabinet.add_server(server)

    @staticmethod
    def move_chassis_server(
        server: Server, from_chassis: Chassis, to_chassis: Chassis
    ) -> None:
        """
        Move a server from one cabinet to another
        :param server: server to move
        :param from_chassis: from
        :param to_chassis: to
        :return: None
        :raises: ValueError if you try to remove a server that doesn't exist
        :raises: IndexError if you try to move a server from or to a chassis that doesn't allow servers
        """
        if not from_chassis.servers or not to_chassis.servers:
            raise IndexError(
                "Cannot move servers from a chassis that doesn't allow servers"
            )
        if not server in from_chassis.servers:
            raise ValueError("Cannot move servers that are not installed.")
        from_chassis.remove_server(server)
        to_chassis.add_server(server)

    @staticmethod
    def move_blade(blade: Blade, from_chassis: Chassis, to_chassis: Chassis) -> None:
        """
        Move a server from one chassis to another
        :param blade: blade to move
        :param from_chassis: from
        :param to_chassis: to
        :return: None
        :raises: ValueError if you try to remove a blade that is not installed
        :raises: IndexError if you try to move a blade from or to a chassis that doesn't allow blades
        """
        if not from_chassis.blades or not to_chassis.blades:
            raise IndexError(
                "Cannot move blades from a chassis that doesn't allow blades"
            )
        if not blade in from_chassis.blades:
            raise ValueError("Cannot move blades that are not installed.")
        from_chassis.remove_blade(blade)
        to_chassis.add_blade(blade)

    @staticmethod
    def swap_disk(
        server: Server, old_disk: Optional[Disk], new_disk: Optional[Disk]
    ) -> None:
        """
        Swap a (broken) disk in a server
        :param server: server to swap disk from/in
        :param old_disk: old disk to remove (if any)
        :param new_disk: new disk to add (if any)
        :return: None
        :raises: ValueError if you try to remove a disk that doesn't exist
        """
        if new_disk is not None:
            server.add_disk(new_disk)
        if old_disk:
            if not server.disks:
                raise ValueError("Cannot remove disks that are not installed.")
            server.remove_disk(old_disk)

    def fetch_server_nic(
        self, row: int, cabinet: int, server: int, nic: int, chassis: Optional[int]
    ) -> NIC:
        """
        Fetch a port from a server NIC
        :param row: Row in DC
        :param cabinet: Cabinet in Row
        :param server: Server in Cabinet/Chassis
        :param nic: NIC in Server
        :param chassis: Chassis in Cabinet (optional)
        :return: NIC object
        :raises: ValueError if any of the indexes are out of bounds
        """
        if row >= len(self.rows):
            raise ValueError("Row does not exist")
        if cabinet >= len(self.rows[row].cabinets):
            raise ValueError("Cabinet does not exist")
        if chassis is not None and chassis >= len(
            self.rows[row].cabinets[cabinet].chassis
        ):
            raise ValueError("Chassis does not exist")
        if server >= len(self.rows[row].cabinets[cabinet].servers):
            raise ValueError("Server does not exist")
        if nic >= len(self.rows[row].cabinets[cabinet].servers[server].nics):
            raise ValueError("NIC does not exist")
        return self.rows[row].cabinets[cabinet].servers[server].nics[nic]
