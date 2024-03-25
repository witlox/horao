# -*- coding: utf-8 -*-#
# [`OSI`] layers
# This module contains the definition of networking activities and their properties.
# We assume that these data structures are prone to change, given that these are configuration artifacts.
# [`OSI`]: https://en.wikipedia.org/wiki/OSI_model

from enum import Enum, auto

from horao.models.status import DeviceStatus


class LinkLayer(Enum):
    Layer2 = auto()
    Layer3 = auto()


class Protocol(Enum):
    TCP = auto()
    UDP = auto()
    ICMP = auto()


class Port:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        mac: str,
        status: DeviceStatus,
        speed_gb: int,
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.mac = mac
        self.status = status
        self.speed_gb = speed_gb


class IpAddress:
    def __init__(self, address: str, netmask: str, gateway: str):
        self.address = address
        self.netmask = netmask
        self.gateway = gateway


class Route:
    def __init__(self, destination: IpAddress, gateway: IpAddress, metric: int):
        self.destination = destination
        self.gateway = gateway
        self.metric = metric


class FirewallRule:
    def __init__(
        self,
        name: str,
        action: str,
        source: IpAddress,
        destination: IpAddress,
        protocol: Protocol,
        port: int,
    ):
        self.name = name
        self.action = action
        self.source = source
        self.destination = destination
        self.protocol = protocol
        self.port = port
