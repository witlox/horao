# -*- coding: utf-8 -*-#
"""Datacenter components

This module contains the definition of compute/storage equipment (hardware) and their properties.
We assume that 'faulty' equipment state is either up or down, it should be handled in a state machine, not here.
Also, we assume that these data structures are not very prone to change, given that this implies a manual activity.
"""
from __future__ import annotations

import logging
from abc import ABC
from typing import Optional, Generic, List, Iterable, TypeVar, Callable

from packify import pack, unpack

from horao.models.crdt import LastWriterWinsMap
from horao.models.decorators import instrument_class_function


class Hardware(ABC):
    def __init__(self, serial_number: str, name: str, model: str, number: int):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number

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

    def pack(self) -> bytes:
        """
        Serialize the hardware instance
        :return: instance as bytes
        """
        return pack([self.serial_number, self.name, self.model, self.number])

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Hardware:
        """
        Deserialize the hardware instance
        :param data: bytes of instance
        :param inject: optional dictionary of global variables
        :return: instance of Hardware
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        serial, name, model, number = unpack(data, inject=inject)
        return cls(serial, name, model, number)


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
        self.size_gb = size_gb
        self.speed_mhz = speed_mhz

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.size_gb,
                self.speed_mhz,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> RAM:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        serial, name, model, number, size_gb, speed_mhz = unpack(data, inject=inject)
        return cls(serial, name, model, number, size_gb, speed_mhz)


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
        self.clock_speed = clock_speed
        self.cores = cores
        self.features = features

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.clock_speed,
                self.cores,
                self.features,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> CPU:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        serial, name, model, number, clock_speed, cores, features = unpack(
            data, inject=inject
        )
        return cls(serial, name, model, number, clock_speed, cores, features)


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
        self.memory_gb = memory_gb
        self.chip = chip
        self.clock_speed = clock_speed

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.memory_gb,
                self.chip,
                self.clock_speed,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Accelerator:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        serial, name, model, number, memory_gb, chip, clock_speed = unpack(
            data, inject=inject
        )
        return cls(serial, name, model, number, memory_gb, chip, clock_speed)


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
        self.size_gb = size_gb

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                self.size_gb,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Disk:
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        serial, name, model, number, size_gb = unpack(data, inject=inject)
        return cls(serial, name, model, number, size_gb)


T = TypeVar("T", bound=Hardware)


class HardwareList(Generic[T]):
    """HardwareList behaves as a list of Hardware instances"""

    def __init__(
        self,
        content: List[T] = None,
        hardware: LastWriterWinsMap = None,
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
        self.hardware = LastWriterWinsMap() if not hardware else hardware
        if content:
            self.extend(content)
        self.iterator = 0

    @instrument_class_function(name="append", level=logging.DEBUG)
    def append(self, item: T) -> T:
        """
        Append a hardware instance to the list
        :param item: instance of Hardware
        :return: inserted item
        """
        self.hardware.set(len(self.hardware), item, hash(item))
        return item

    def clear(self) -> None:
        """
        Clear the list, not the history
        :return: None
        """
        # todo check history is consistent
        self.iterator = 0
        self.hardware = LastWriterWinsMap()

    def copy(self) -> HardwareList[T]:
        results = HardwareList(inject=self.inject)
        results.extend(iter(self))
        return results

    def count(self):
        return len(self)

    def extend(self, other: Iterable[T]) -> HardwareList[T]:
        for item in other:
            self.hardware.set(len(self), item, hash(item))
        return self

    def index(self, item: T) -> int:
        """
        Return the index of the hardware instance
        :param item: instance to search for
        :return: int
        :raises ValueError: item not found
        """
        result = next(
            iter([i for i, h in self.hardware.read(inject=self.inject) if h == item]),
            None,
        )
        if result is None:
            self.log.error(f"{item.name} not found.")
            raise ValueError(f"{item} not found.")
        return result

    def insert(self, index: int, item: T) -> None:
        self.hardware.set(index, item, hash(item))

    @instrument_class_function(name="pop", level=logging.DEBUG)
    def pop(self, index: int, default: T = None) -> Optional[T]:
        if index >= len(self.hardware.read(inject=self.inject)):
            self.log.debug(f"Index {index} out of bounds, returning default.")
            return default
        item = self.hardware.read(inject=self.inject)[index]
        self.hardware.unset(item, hash(item))
        return item

    @instrument_class_function(name="remove", level=logging.DEBUG)
    def remove(self, item: T) -> None:
        """
        Remove a hardware instance from the list
        :param item: instance of Hardware
        :return: None
        :raises ValueError: item not found
        """
        local_item = next(
            iter([h for _, h in self.hardware.read(inject=self.inject) if h == item]),
            None,
        )
        if not local_item:
            self.log.debug(f"{item.name} not found.")
            raise ValueError(f"{item} not found.")
        self.hardware.unset(local_item, hash(item))

    def reverse(self) -> None:
        """
        cannot reverse a list inplace in a CRDT
        :return: None
        :raises: NotImplementedError
        """
        raise NotImplementedError("Cannot reverse a list inplace in a CRDT")

    def sort(self, item: T = None, reverse: bool = False) -> None:
        """
        cannot sort a list inplace in a CRDT
        :return: None
        :raises: NotImplementedError
        """
        raise NotImplementedError("Cannot sort a list inplace in a CRDT")

    def __len__(self) -> int:
        return len(self.hardware.read(inject=self.inject))

    def __eq__(self, other: HardwareList[T]) -> bool:
        return self.hardware.read(inject=self.inject) == other.hardware.read(
            inject=self.inject
        )

    def __ne__(self, other: HardwareList[T]) -> bool:
        return self.hardware.read(inject=self.inject) != other.hardware.read(
            inject=self.inject
        )

    def __contains__(self, item: T) -> bool:
        return item in self.hardware.read(inject=self.inject)

    def __delitem__(self, item: T) -> None:
        if item not in self.hardware.read(inject=self.inject):
            raise KeyError(f"{item} not found.")
        self.remove(item)

    def __getitem__(self, index: int) -> T:
        return self.hardware.read(inject=self.inject)[index]

    def __setitem__(self, index: int, value: T) -> None:
        self.hardware.set(index, value, hash(value))

    def __iter__(self) -> Iterable[T]:
        for _, item in self.hardware.read(inject=self.inject):
            yield item

    def __next__(self) -> T:
        if self.iterator >= len(self.hardware.read(inject=self.inject)):
            self.iterator = 0
            raise StopIteration
        item = self.hardware.read(inject=self.inject)[self.iterator]
        self.iterator += 1
        return item

    def __add__(self, other: HardwareList[T]) -> HardwareList[T]:
        return self.extend(iter(other))

    def __sub__(self, other: HardwareList[T]) -> HardwareList[T]:
        for item in iter(other):
            self.remove(item)
        return self

    def __repr__(self) -> str:
        return f"HardwareList({self.hardware.read(inject=self.inject)})"

    def __reversed__(self) -> HardwareList[T]:
        return self.hardware.read(inject=self.inject)[::-1]

    def __sizeof__(self) -> int:
        return self.count()

    def __hash__(self):
        return hash(self.hardware)

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes
        """
        return self.hardware.pack()

    @classmethod
    def unpack(cls, data: bytes, /, *, inject=None) -> HardwareList[T]:
        """
        Unpack the data bytes string into an instance.
        :param data: serialized FractionallyIndexedArray needing unpacking
        :param inject: optional data to inject during unpacking
        :return: FractionallyIndexedArray
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        positions = LastWriterWinsMap.unpack(data, inject)
        return cls(hardware=positions, inject=inject)
