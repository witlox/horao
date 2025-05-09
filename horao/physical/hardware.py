# -*- coding: utf-8 -*-#
"""Somewhat abstract physical 'hardware'."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar

from horao.conceptual.crdt import CRDTList, LastWriterWinsMap


class Hardware(ABC):
    """Base class for hardware components and composites."""

    def __init__(self, serial_number: str, model: str, number: int):
        """
        Initialize a hardware instance
        :param serial_number: serial number
        :param model: model
        :param number: 1-indexed number of the hardware instance in a composite
        """
        self.serial_number = serial_number
        self.model = model
        self.number = number

    def __copy__(self):
        return Hardware(self.serial_number, self.model, self.number)

    def __eq__(self, other) -> bool:
        """
        Compare two hardware instances by serial and number
        :param other: instance of Hardware
        :return: bool
        """
        if not isinstance(other, Hardware):
            return False
        if self.serial_number != other.serial_number:
            return False
        if not (self.model == other.model and self.number == other.number):
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
        return hash((self.serial_number, self.model))


T = TypeVar("T", bound=Hardware)


class HardwareList(CRDTList[T]):
    def __init__(
        self,
        hardware: Optional[List[T]] = None,
        items: Optional[LastWriterWinsMap] = None,
    ):
        super().__init__(hardware, items)
