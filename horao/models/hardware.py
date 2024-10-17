# -*- coding: utf-8 -*-#
"""Datacenter hardware (compute & storage)

This module contains the definition of compute/storage equipment (hardware) and their properties.
We assume that 'faulty' equipment state is either up or down, it should be handled in a state machine, not here.
Also, we assume that these data structures are not very prone to change, given that this implies a manual activity.
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


class Module:
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


class Node:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        modules: List[Module],
        status: DeviceStatus,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.modules = modules
        self.status = status


class Blade:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        nodes: List[Node],
        status: DeviceStatus,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.nodes = nodes
        self.status = status


class Chassis:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        servers: Optional[List[Server]],
        blades: Optional[List[Blade]],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.servers = servers
        self.blades = blades


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
            if not server.disk:
                server.disk = []
            server.disk.append(new_disk)
        if old_disk:
            if not server.disk:
                raise ValueError("Cannot remove disks that are not installed.")
            server.disk.remove(old_disk)

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
