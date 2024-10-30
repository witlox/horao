# -*- coding: utf-8 -*-#
"""Hardware components

This module contains the definition of computer components and their properties.
We assume that these data structures are not very prone to change, given that this implies a manual activity.
"""
from __future__ import annotations

from typing import Optional

from horao.physical.hardware import Hardware


class RAM(Hardware):
    def __init__(
        self,
        serial_number: str,
        model: str,
        number: int,
        size_gb: int,
        speed_mhz: Optional[int],
    ):
        super().__init__(serial_number, model, number)
        self.size_gb = size_gb
        self.speed_mhz = speed_mhz

    def __copy__(self):
        return RAM(
            self.serial_number,
            self.model,
            self.number,
            self.size_gb,
            self.speed_mhz,
        )


class CPU(Hardware):
    def __init__(
        self,
        serial_number: str,
        model: str,
        number: int,
        clock_speed: float,
        cores: int,
        features: Optional[str],
    ):
        super().__init__(serial_number, model, number)
        self.clock_speed = clock_speed
        self.cores = cores
        self.features = features

    def __copy__(self):
        return CPU(
            self.serial_number,
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
        model: str,
        number: int,
        memory_gb: int,
        chip: Optional[str],
        clock_speed: Optional[int],
    ):
        super().__init__(serial_number, model, number)
        self.memory_gb = memory_gb
        self.chip = chip
        self.clock_speed = clock_speed

    def __copy__(self):
        return Accelerator(
            self.serial_number,
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
        model: str,
        number: int,
        size_gb: int,
    ):
        super().__init__(serial_number, model, number)
        self.size_gb = size_gb

    def __copy__(self):
        return Disk(self.serial_number, self.model, self.number, self.size_gb)
