# -*- coding: utf-8 -*-#
"""Somewhat abstract physical 'hardware'."""
from __future__ import annotations

from abc import ABC
from typing import List, TypeVar

from horao.conceptual.crdt import CRDTList, LastWriterWinsMap


class Hardware(ABC):
    """Base class for hardware components and composites."""

    def __init__(self, serial_number: str, name: str, model: str, number: int):
        """
        Initialize a hardware instance
        :param serial_number: serial number
        :param name: name
        :param model: model
        :param number: 1-indexed number of the hardware instance in a composite
        """
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


T = TypeVar("T", bound=Hardware)


class HardwareList(CRDTList[T]):
    def __init__(self, hardware: List[T] = None, items: LastWriterWinsMap = None):
        super().__init__(hardware, items)
