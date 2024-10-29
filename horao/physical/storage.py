# -*- coding: utf-8 -*-#
"""Storage hardware."""
from __future__ import annotations

from enum import Enum, auto


class StorageClass(Enum):
    """Available storage classes"""

    Hot = auto()
    Warm = auto()
    Cold = auto()


class StorageType(Enum):
    """Available storage types"""

    Block = auto()
    Object = auto()
