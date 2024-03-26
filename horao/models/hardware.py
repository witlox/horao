# -*- coding: utf-8 -*-#
"""Datacenter hardware (compute & storage)

This module contains the definition of compute/storage equipment (hardware) and their properties.
We assume that 'faulty' equipment state is either up or down, it should be handled in a state machine, not here.
Also we assume that these data structures are not very prone to change, given that this implies a manual activity.
"""
from typing import List, Optional

from horao.models import Port, Switch
from horao.models.network import NIC
from horao.models.status import DeviceStatus


class RAM:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        size_gb: int,
        speed_mhz: Optional[int],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.size_gb = size_gb
        self.speed_mhz = speed_mhz


class CPU:
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
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.clock_speed = clock_speed
        self.cores = cores
        self.features = features


class Accelerator:
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
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.memory_gb = memory_gb
        self.chip = chip
        self.clock_speed = clock_speed


class Disk:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        size_gb: int,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.size_gb = size_gb


class Server:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpu: List[CPU],
        ram: List[RAM],
        nic: List[NIC],
        disk: Optional[List[Disk]],
        accelerator: Optional[List[Accelerator]],
        status: DeviceStatus,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.cpu = cpu
        self.ram = ram
        self.nic = nic
        self.disk = disk
        self.accelerator = accelerator
        self.status = status


class Chassis:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        servers: List[Server],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.servers = servers


class Cabinet:
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
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.servers = servers
        self.chassis = chassis
        self.switches = switches


class Row:
    def __init__(self, name, number, cabinets):
        self.name = name
        self.number = number
        self.cabinets = cabinets


class DataCenter:
    def __init__(self, name: str, number: int, rows: List[Row]):
        self.name = name
        self.number = number
        self.rows = rows

    @staticmethod
    def move_server(server: Server, from_cabinet: Cabinet, to_cabinet: Cabinet) -> None:
        """
        Move a server from one cabinet to another
        :param server: server to move
        :param from_cabinet: from
        :param to_cabinet: to
        :return: None
        """
        from_cabinet.servers.remove(server)
        to_cabinet.servers.append(server)

    @staticmethod
    def move_blade(server: Server, from_chassis: Chassis, to_chassis: Chassis) -> None:
        """
        Move a server from one chassis to another
        :param server: server to move (usually a blade)
        :param from_chassis: from
        :param to_chassis: to
        :return: None
        """
        from_chassis.servers.remove(server)
        to_chassis.servers.append(server)

    @staticmethod
    def swap_disk(server: Server, old_disk: Disk, new_disk: Disk) -> None:
        """
        Swap a (broken) disk in a server
        :param server: server to swap disk from/in
        :param old_disk: old disk to remove
        :param new_disk: new disk to add
        :return: None
        """
        server.disk.remove(old_disk)
        server.disk.append(new_disk)

    def fetch_server_nic(
        self,
        row: int,
        cabinet: int,
        server: int,
        nic: int,
        chassis: Optional[int]
    ) -> NIC:
        """
        Fetch a port from a server NIC
        :param row: Row in DC
        :param cabinet: Cabinet in Row
        :param server: Server in Cabinet/Chassis
        :param nic: NIC in Server
        :param chassis: Chassis in Cabinet (optional)
        :return: NIC object
        :raises: ValueError if any of the indexes is out of bounds
        """
        if row >= len(self.rows):
            raise ValueError("Row does not exist")
        if cabinet >= len(self.rows[row].cabinets):
            raise ValueError("Cabinet does not exist")
        if chassis is not None and chassis >= len(
            self.rows[row].cabinets[cabinet].chassis
        ):
            raise ValueError("Chassis does not exist")
        if server >= len(self.rows[row].cabinets[cabinet].servers):
            raise ValueError("Server does not exist")
        if nic >= len(self.rows[row].cabinets[cabinet].servers[server].nic):
            raise ValueError("NIC does not exist")
        return self.rows[row].cabinets[cabinet].servers[server].nic[nic]
