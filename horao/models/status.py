# -*- coding: utf-8 -*-#
# States that we are able to manage

from enum import Enum, auto


class DeviceStatus(Enum):
    Up = auto()
    Down = auto()
