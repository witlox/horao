# -*- coding: utf-8 -*-#
"""Datacenter components

This module contains the definition of compute/storage equipment (hardware) and their properties.
We assume that 'faulty' equipment state is either up or down, it should be handled in a state machine, not here.
Also, we assume that these data structures are not very prone to change, given that this implies a manual activity.
"""
from __future__ import annotations

from abc import ABC
from typing import List, Optional, TypeVar

from horao.models.crdt import CRDTList, LastWriterWinsMap


class Hardware(ABC):
    def __init__(self, serial_number: str, name: str, model: str, number: int):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number

    def __copy__(self):
        return Hardware(self.serial_number, self.name, self.model, self.number)

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
        return self.number > other.number

    def __lt__(self, other: Hardware) -> bool:
        """
        Compare two hardware instances by serial number
        :param other: instance of Hardware
        :return: bool
        """
        return self.number < other.number

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
        self.size_gb = size_gb
        self.speed_mhz = speed_mhz

    def __copy__(self):
        return RAM(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            self.size_gb,
            self.speed_mhz,
        )


class CPU(Hardware):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        clock_speed: float,
        cores: int,
        features: Optional[str],
    ):
        super().__init__(serial_number, name, model, number)
        self.clock_speed = clock_speed
        self.cores = cores
        self.features = features

    def __copy__(self):
        return CPU(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            self.clock_speed,
            self.cores,
            self.features,
        )


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

    def __copy__(self):
        return Accelerator(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            self.memory_gb,
            self.chip,
            self.clock_speed,
        )


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

    def __copy__(self):
        return Disk(
            self.serial_number, self.name, self.model, self.number, self.size_gb
        )


T = TypeVar("T", bound=Hardware)


class HardwareList(CRDTList[T]):
    def __init__(self, hardware: List[T] = None, items: LastWriterWinsMap = None):
        super().__init__(hardware, items)
