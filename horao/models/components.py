# -*- coding: utf-8 -*-#
"""Datacenter components

This module contains the definition of compute/storage equipment (hardware) and their properties.
We assume that 'faulty' equipment state is either up or down, it should be handled in a state machine, not here.
Also, we assume that these data structures are not very prone to change, given that this implies a manual activity.
"""
from __future__ import annotations

import logging
from abc import ABC
from typing import Optional, Generic, List, Iterable, TypeVar

from horao.crdts import FractionallyIndexedArray
from horao.crdts.data_types import Integer, Nothing, String, Float
from horao.models.decorators import instrument_class_function


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
    """HardwareList behaves as a list of Hardware instances"""

    def __init__(self, content: List[T] = None, inject=None) -> None:
        self._inject = {**globals()} if not inject else {**globals(), **inject}
        self._log = logging.getLogger(__name__)
        self._hardware = FractionallyIndexedArray()
        if content:
            self.extend(content)

    @instrument_class_function(name="append", level=logging.DEBUG)
    def append(self, item: T) -> T:
        """
        Append a hardware instance to the list
        :param item: instance of Hardware
        :return: None
        """
        if not isinstance(item, Hardware):
            raise ValueError("Cannot append non-hardware instance to HardwareList")
        clock_uuid, time_stamp, data = self._hardware.put_first(
            item, item.name, inject=self._inject
        )
        self._log.debug(
            f"Added {item.name} (clock_uuid={clock_uuid}, time_stamp={time_stamp})"
        )
        return item

    def clear(self) -> None:
        self._hardware = FractionallyIndexedArray()

    def copy(self) -> HardwareList[T]:
        results = HardwareList(inject=self._inject)
        results.extend(self.iter())
        return results

    def count(self):
        return len(self._hardware.read_full())

    def extend(self, other: Iterable[T]) -> HardwareList[T]:
        for item in other:
            self._hardware.append(item, hash(item))
        return self

    def index(self, item: T) -> Optional[T]:
        return next(
            iter([i for i, h in enumerate(self._hardware.read_full()) if h == item]),
            None,
        )

    def insert(self, index: int, item: T) -> None:
        self._hardware.put(item, hash(item), Float(index), inject=self._inject)

    @instrument_class_function(name="pop", level=logging.DEBUG)
    def pop(self, index: int, default: T = None) -> Optional[T]:
        if index >= len(self._hardware.read_full()):
            return default
        item = self._hardware.read_full(inject=self._inject)[index]
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
            iter(
                [h for h in self._hardware.read_full(inject=self._inject) if h == item]
            ),
            None,
        )
        if not fi_hardware:
            self._log.error(f"{item.name} not found.")
        clock_uuid, time_stamp, data = self._hardware.delete(
            fi_hardware, item.name, inject=self._inject
        )
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
        return self._hardware.read_full(inject=self._inject).sort(
            key=item, reverse=reverse
        )

    def __len__(self) -> int:
        return self.len()

    def __eq__(self, other: HardwareList[T]) -> bool:
        return self._hardware.read_full(
            inject=self._inject
        ) == other._hardware.read_full(inject=self._inject)

    def __ne__(self, other: HardwareList[T]) -> bool:
        return self._hardware.read_full(
            inject=self._inject
        ) != other._hardware.read_full(inject=self._inject)

    def __ge__(self, other: HardwareList[T]) -> bool:
        return self._hardware.read_full(
            inject=self._inject
        ) >= other._hardware.read_full(inject=self._inject)

    def __gt__(self, other: HardwareList[T]) -> bool:
        return self._hardware.read_full(
            inject=self._inject
        ) > other._hardware.read_full(inject=self._inject)

    def __le__(self, other: HardwareList[T]):
        return self._hardware.read_full(
            inject=self._inject
        ) <= other._hardware.read_full(inject=self._inject)

    def __lt__(self, other: HardwareList[T]):
        return self._hardware.read_full(
            inject=self._inject
        ) < other._hardware.read_full(inject=self._inject)

    def __contains__(self, item: T) -> bool:
        return item in self._hardware.read_full(inject=self._inject)

    def __delitem__(self, item: T) -> None:
        if item not in self._hardware.read_full(inject=self._inject):
            raise KeyError(f"{item} not found.")
        self.remove(item)

    def __getattr__(self, item: T) -> T:
        return self._hardware.read_full(inject=self._inject)[item]

    def __getitem__(self, index: int) -> T:
        return self._hardware.read_full(inject=self._inject)[index]

    def __setitem__(self, index: int, value: T) -> None:
        self._hardware.put(value, hash(value), Float(index))

    def __iter__(self) -> Iterable[T]:
        for item in self._hardware.read_full(inject=self._inject):
            yield item

    def __next__(self) -> T:
        return next(self._hardware.read_full(inject=self._inject))

    def __mul__(self, other: HardwareList[T]):
        raise TypeError("Cannot multiply HardwareList")

    def __add__(self, other: HardwareList[T]) -> HardwareList[T]:
        return self.extend(other.iter())

    def __sub__(self, other: HardwareList[T]) -> HardwareList[T]:
        for item in other.iter():
            self.remove(item)
        return self

    def __repr__(self) -> str:
        return f"HardwareList({self._hardware.read_full()})"

    def __reversed__(self) -> HardwareList[T]:
        return self.reverse()

    def __sizeof__(self) -> int:
        return self.count()

    def __hash__(self):
        return hash(self._hardware)
