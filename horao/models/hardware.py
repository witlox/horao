# -*- coding: utf-8 -*-#
# Datacenter hardware (compute & storage)
#
# This module contains the definition of compute/storage equipment (hardware) and their properties.
# We assume that 'faulty' equipment state is either up or down, it should be handled in a state machine, not here.
# Also we assume that these data structures are not very prone to change, given that this implies a manual activity.

from horao.models.status import DeviceStatus


class RAM:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        size_gb: int,
        speed_mhz: int,
        usage_gb: int,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.size_gb = size_gb
        self.speed_mhz = speed_mhz
        self.usage_gb = usage_gb


class NIC:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        mac: str,
        link_status: DeviceStatus,
        port_speed_gbps: int,
        number_of_ports: int,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.mac = mac
        self.link_status = link_status
        self.port_speed_gbps = port_speed_gbps
        self.number_of_ports = number_of_ports


class CPU:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        clock_speed: int,
        cores: int,
        features: str,
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
        chip: str,
        clock_speed: int,
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
        usage_gb: int,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.size_gb = size_gb
        self.usage_gb = usage_gb


class Server:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpu: list[CPU],
        ram: list[RAM],
        disk: list[Disk],
        nic: list[NIC],
        accelerator: list[Accelerator],
        status: DeviceStatus,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.cpu = cpu
        self.ram = ram
        self.disk = disk
        self.nic = nic
        self.accelerator = accelerator
        self.status = status


class Row:
    def __init__(self, name, number, cabinets):
        self.name = name
        self.number = number
        self.cabinets = cabinets


class Chassis:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        servers: list[Server],
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
        servers: list[Server],
        chassis: list[Chassis],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.servers = servers
        self.chassis = chassis


class DataCenter:
    def __init__(self, name: str, number: int, rows: list[Row]):
        self.name = name
        self.number = number
        self.rows = rows
