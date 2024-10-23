# -*- coding: utf-8 -*-#
"""Data Center composites"""
from __future__ import annotations

import logging
from typing import List, Optional, Dict, Tuple, Iterable

from horao.crdts import LastWriterWinsMap
from horao.crdts.data_types import String
from .composite import Server, Chassis, Disk, NIC, ComputerList
from .network import Switch
from .components import Hardware, HardwareList
from .composite import Blade
from .decorators import instrument_class_function


class Cabinet(Hardware):
    """A cabinet is a physical rack that hosts servers, chassis, and switches"""

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
        self.servers = ComputerList[Server]().extend(servers)
        self.chassis = HardwareList[Chassis]().extend(chassis)
        self.switches = HardwareList[Switch]().extend(switches)


class DataCenter:
    """Data Center model
    Behaves as a dictionary
    Each pair of the dictionary is a row in the data center
    The key is the row number, the value is a list of cabinets
    """

    def __init__(self, name: str, number: int):
        self._log = logging.getLogger(__name__)
        self._name = String(name)
        self._number = number
        self._rows = LastWriterWinsMap()

    @property
    def name(self) -> str:
        return self._name.value

    @property
    def number(self) -> int:
        return self._number

    def clear(self) -> None:
        self._rows = LastWriterWinsMap()

    @instrument_class_function(name="copy", level=logging.DEBUG)
    def copy(self) -> Dict[int, List[Cabinet]]:
        result = {}
        for key, v in self._rows.read():
            result[key] = v.value
        return result

    @instrument_class_function(name="has_key", level=logging.DEBUG)
    def has_key(self, k: int) -> bool:
        for key, _ in self._rows.read():
            if key == k:
                return True
        return False

    def update(self, key: int, value: List[Cabinet]) -> None:
        self._rows.set(key, value, key)

    def keys(self) -> List[int]:
        return [k for k, _ in self._rows.read()]

    def values(self) -> List[List[Cabinet]]:
        return [v for _, v in self._rows.read()]

    def items(self) -> List[Tuple[int, List[Cabinet]]]:
        return [(k, v) for k, v in self._rows.read()]

    @instrument_class_function(name="pop", level=logging.DEBUG)
    def pop(self, key: int) -> List[Cabinet]:
        for k, v in self._rows.read():
            if k == key:
                self._rows.unset(key, key)
                return v.value
        raise KeyError(f"Key {key} not found")

    def __eq__(self, other: DataCenter) -> bool:
        return self.name == other.name and self.number == other.number

    def __ne__(self, other: DataCenter) -> bool:
        return not self == other

    def __setitem__(self, key: int, item: List[Cabinet]) -> None:
        self._rows.set(key, item, key)

    @instrument_class_function(name="getitem", level=logging.DEBUG)
    def __getitem__(self, key):
        for k, v in self._rows.read():
            if k == key:
                return v.value
        raise KeyError(f"Key {key} not found")

    @instrument_class_function(name="delitem", level=logging.DEBUG)
    def __delitem__(self, key):
        for k, v in self._rows.read():
            if k == key:
                self._rows.unset(key, key)
                return
        raise KeyError(f"Key {key} not found")

    def __repr__(self) -> str:
        return f"DataCenter({self.name}, {self.number})"

    def __len__(self) -> int:
        return len(self._rows.read())

    def __contains__(self, cabinet: Cabinet) -> bool:
        for _, v in self._rows.read():
            if cabinet in v:
                return True
        return False

    def __iter__(self) -> Iterable[Tuple[int, List[Cabinet]]]:
        for k, v in self.items():
            yield k, v

    def __hash__(self) -> int:
        return hash((self.name, self.number))

    @staticmethod
    def move_server(server: Server, from_cabinet: Cabinet, to_cabinet: Cabinet) -> None:
        """
        Move a server from one cabinet to another
        :param server: server to move
        :param from_cabinet: from
        :param to_cabinet: to
        :return: None
        :raises: ValueError if you try to remove a server that doesn't exist
        """
        if not server in from_cabinet.servers:
            raise ValueError("Cannot move servers that are not installed.")
        from_cabinet.servers.remove(server)
        to_cabinet.servers.append(server)

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
        from_chassis.servers.remove(server)
        to_chassis.servers.append(server)

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
        from_chassis.blades.remove(blade)
        to_chassis.blades.append(blade)

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
            server.disks.append(new_disk)
        if old_disk:
            if not server.disks:
                raise ValueError("Cannot remove disks that are not installed.")
            server.disks.remove(old_disk)

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
        if row >= len(self):
            raise ValueError("Row does not exist")
        if cabinet >= len(self[row].cabinets):
            raise ValueError("Cabinet does not exist")
        if chassis is not None and chassis >= len(self[row].cabinets[cabinet].chassis):
            raise ValueError("Chassis does not exist")
        if server >= len(self[row].cabinets[cabinet].servers):
            raise ValueError("Server does not exist")
        if nic >= len(self[row].cabinets[cabinet].servers[server].nics):
            raise ValueError("NIC does not exist")
        return self[row].cabinets[cabinet].servers[server].nics[nic]
