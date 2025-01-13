# -*- coding: utf-8 -*-#
"""Base Controller for synchronization infrastructural state."""

from abc import ABC, abstractmethod
from typing import Dict, List

from horao.logical.data_center import DataCenter, DataCenterNetwork


class BaseController(ABC):

    def __init__(self, datacenters: Dict[DataCenter, List[DataCenterNetwork]]) -> None:
        self.datacenters = datacenters

    @abstractmethod
    def sync(self):
        pass

    @abstractmethod
    def subscribe(self):
        pass
