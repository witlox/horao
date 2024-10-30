# -*- coding: utf-8 -*-#
"""Serialize and Deserialize Horao objects to JSON"""
import json
from datetime import date, datetime
from multiprocessing.resource_tracker import register
from typing import Any, Tuple

from networkx.convert import from_dict_of_dicts, to_dict_of_dicts

from horao.conceptual.crdt import (
    LastWriterWinsMap,
    LastWriterWinsRegister,
    ObservedRemovedSet,
)
from horao.conceptual.osi_layers import LinkLayer
from horao.conceptual.support import LogicalClock, Update, UpdateType
from horao.logical.data_center import DataCenter, DataCenterNetwork
from horao.logical.infrastructure import LogicalInfrastructure
from horao.physical.component import CPU, RAM, Accelerator, Disk
from horao.physical.composite import Blade, Cabinet, Chassis, Node
from horao.physical.computer import Module, Server
from horao.physical.hardware import HardwareList
from horao.physical.network import (
    NIC,
    Firewall,
    NetworkType,
    Port,
    Router,
    RouterType,
    Switch,
    SwitchType,
)
from horao.physical.status import DeviceStatus


class HoraoEncoder(json.JSONEncoder):
    """HoraoEncoder is a class that is used to serialize Horao objects to JSON"""

    def default(self, obj):
        """
        Serialize Horao objects to JSON.
        Note that float NaN and Infinity are not supported.
        :param obj: object to serialize
        :return: JSON object
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, set):
            return {"type": "Set", "value": list(obj)}
        if isinstance(obj, LogicalClock):
            return {
                "type": "LogicalClock",
                "time_stamp": obj.time_stamp,
                "uuid": obj.uuid.hex(),
                "offset": obj.offset,
            }
        if isinstance(obj, Update):
            return {
                "type": "Update",
                "clock_uuid": obj.clock_uuid.hex(),
                "time_stamp": obj.time_stamp,
                "data": json.dumps(obj.data, cls=HoraoEncoder) if obj.data else None,
                "update_type": obj.update_type.value,
                "writer": obj.writer,
                "name": obj.name,
            }
        if isinstance(obj, ObservedRemovedSet):
            return {
                "type": "ObservedRemovedSet",
                "observed": json.dumps(obj.observed, cls=HoraoEncoder),
                "observed_metadata": json.dumps(
                    obj.observed_metadata, cls=HoraoEncoder
                ),
                "removed": json.dumps(obj.removed, cls=HoraoEncoder),
                "removed_metadata": json.dumps(obj.removed_metadata, cls=HoraoEncoder),
                "clock": json.dumps(obj.clock, cls=HoraoEncoder),
                "listeners": json.dumps(obj.listeners, cls=HoraoEncoder),
            }
        if isinstance(obj, LastWriterWinsRegister):
            return {
                "type": "LastWriterWinsRegister",
                "name": json.dumps(obj.name, cls=HoraoEncoder),
                "value": json.dumps(obj.value, cls=HoraoEncoder) if obj.clock else None,
                "clock": json.dumps(obj.clock, cls=HoraoEncoder) if obj.clock else None,
                "last_update": obj.last_update,
                "last_writer": obj.last_writer,
                "listeners": (
                    json.dumps(obj.listeners, cls=HoraoEncoder)
                    if obj.listeners
                    else None
                ),
            }
        if isinstance(obj, LastWriterWinsMap):
            result = {
                "type": "LastWriterWinsMap",
                "names": json.dumps(obj.names, cls=HoraoEncoder) if obj.names else None,
                "listeners": (
                    json.dumps(obj.listeners, cls=HoraoEncoder)
                    if obj.listeners
                    else None
                ),
            }
            registers = {}
            if obj.registers:
                for k, v in obj.registers.items():
                    registers[json.dumps(k, cls=HoraoEncoder)] = json.dumps(
                        v, cls=HoraoEncoder
                    )
            result["registers"] = registers
            return result
        if isinstance(obj, HardwareList):
            return {
                "type": "HardwareList",
                "hardware": json.dumps(obj.hardware, cls=HoraoEncoder),
            }
        if isinstance(obj, Port):
            return {
                "type": "Port",
                "serial_number": obj.serial_number,
                "model": obj.model,
                "number": obj.number,
                "mac": obj.mac,
                "status": obj.status.value,
                "connected": False,
                "speed_gb": obj.speed_gb,
            }
        if isinstance(obj, NIC):
            return {
                "type": "NIC",
                "serial_number": obj.serial_number,
                "model": obj.model,
                "number": obj.number,
                "ports": json.dumps(obj.ports, cls=HoraoEncoder),
            }
        if isinstance(obj, Switch):
            return {
                "type": "Switch",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "layer": obj.layer.value,
                "switch_type": obj.switch_type.value,
                "status": obj.status.value,
                "managed": obj.managed,
                "lan_ports": json.dumps(obj.ports, cls=HoraoEncoder),
                "uplink_ports": (
                    json.dumps(obj.uplink_ports, cls=HoraoEncoder)
                    if obj.uplink_ports
                    else None
                ),
            }
        if isinstance(obj, Router):
            return {
                "type": "Router",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "router_type": obj.router_type.value,
                "status": obj.status.value,
                "lan_ports": json.dumps(obj.ports, cls=HoraoEncoder),
                "wan_ports": (
                    json.dumps(obj.wan_ports, cls=HoraoEncoder)
                    if obj.wan_ports
                    else None
                ),
            }
        if isinstance(obj, Firewall):
            return {
                "type": "Firewall",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "status": obj.status.value,
                "lan_ports": json.dumps(obj.ports, cls=HoraoEncoder),
                "wan_ports": (
                    json.dumps(obj.wan_ports, cls=HoraoEncoder)
                    if obj.wan_ports
                    else None
                ),
            }
        if isinstance(obj, CPU):
            return {
                "type": "CPU",
                "serial_number": obj.serial_number,
                "model": obj.model,
                "number": obj.number,
                "clock_speed": obj.clock_speed,
                "cores": obj.cores,
                "features": obj.features,
            }
        if isinstance(obj, RAM):
            return {
                "type": "RAM",
                "serial_number": obj.serial_number,
                "model": obj.model,
                "number": obj.number,
                "size_gb": obj.size_gb,
                "speed_mhz": obj.speed_mhz,
            }
        if isinstance(obj, Accelerator):
            return {
                "type": "Accelerator",
                "serial_number": obj.serial_number,
                "model": obj.model,
                "number": obj.number,
                "memory_gb": obj.memory_gb,
                "chip": obj.chip,
                "clock_speed": obj.clock_speed,
            }
        if isinstance(obj, Disk):
            return {
                "type": "Disk",
                "serial_number": obj.serial_number,
                "model": obj.model,
                "number": obj.number,
                "size_gb": obj.size_gb,
            }
        if isinstance(obj, Server):
            return {
                "type": "Server",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "cpus": json.dumps(obj.cpus, cls=HoraoEncoder),
                "rams": json.dumps(obj.rams, cls=HoraoEncoder),
                "nics": json.dumps(obj.nics, cls=HoraoEncoder),
                "disks": json.dumps(obj.disks, cls=HoraoEncoder) if obj.disks else None,
                "accelerators": (
                    json.dumps(obj.accelerators, cls=HoraoEncoder)
                    if obj.accelerators
                    else None
                ),
                "status": obj.status.value,
            }
        if isinstance(obj, Module):
            return {
                "type": "Module",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "cpus": json.dumps(obj.cpus, cls=HoraoEncoder),
                "rams": json.dumps(obj.rams, cls=HoraoEncoder),
                "nics": json.dumps(obj.nics, cls=HoraoEncoder),
                "disks": json.dumps(obj.disks, cls=HoraoEncoder) if obj.disks else None,
                "accelerators": (
                    json.dumps(obj.accelerators, cls=HoraoEncoder)
                    if obj.accelerators
                    else None
                ),
                "status": obj.status.value,
            }
        if isinstance(obj, Node):
            return {
                "type": "Node",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "modules": (
                    json.dumps(obj.modules, cls=HoraoEncoder) if obj.modules else None
                ),
            }
        if isinstance(obj, Blade):
            return {
                "type": "Blade",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "nodes": (
                    json.dumps(obj.nodes, cls=HoraoEncoder) if obj.nodes else None
                ),
            }
        if isinstance(obj, Chassis):
            return {
                "type": "Chassis",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "servers": (
                    json.dumps(obj.servers, cls=HoraoEncoder) if obj.servers else None
                ),
                "blades": (
                    json.dumps(obj.blades, cls=HoraoEncoder) if obj.blades else None
                ),
            }
        if isinstance(obj, Cabinet):
            return {
                "type": "Cabinet",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "servers": (
                    json.dumps(obj.servers, cls=HoraoEncoder) if obj.servers else None
                ),
                "chassis": (
                    json.dumps(obj.chassis, cls=HoraoEncoder) if obj.chassis else None
                ),
                "switches": (
                    json.dumps(obj.switches, cls=HoraoEncoder) if obj.switches else None
                ),
            }
        if isinstance(obj, DataCenter):
            result = {
                "type": "DataCenter",
                "name": obj.name,
                "number": obj.number,
            }
            rows = []
            for row in obj.rows.read():
                rows = json.dumps(row, cls=HoraoEncoder)
            result["rows"] = rows if rows else None
            return result
        if isinstance(obj, DataCenterNetwork):
            return {
                "type": "DataCenterNetwork",
                "name": obj.name,
                "network_type": obj.network_type.value,
                "graph": json.dumps(
                    to_dict_of_dicts(obj.hash_graph()), cls=HoraoEncoder
                ),
                "nodes": json.dumps(obj.nodes(), cls=HoraoEncoder),
                "hsn": obj.hsn if obj.hsn else False,
            }
        if isinstance(obj, LogicalInfrastructure):
            result = {
                "type": "LogicalInfrastructure",
                "infrastructure": {},
                "constraints": {},
                "claims": [],
            }
            for k, v in obj.infrastructure.items():
                result["infrastructure"][json.dumps(k, cls=HoraoEncoder)] = json.dumps(
                    v, cls=HoraoEncoder
                )
            for k, v in obj.constraints.items():
                result["constraints"][json.dumps(k, cls=HoraoEncoder)] = json.dumps(
                    v, cls=HoraoEncoder
                )
            for c in obj.claims:
                result["claims"].append(json.dumps(c, cls=HoraoEncoder))
            return result
        return json.JSONEncoder.default(self, obj)


class HoraoDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj):
        if "date" in obj:
            return datetime.strptime(obj["date"], "%Y-%m-%d")
        if "type" in obj and obj["type"] == "Set":
            return set(obj["value"])
        if "type" in obj and obj["type"] == "LogicalClock":
            return LogicalClock(
                time_stamp=obj["time_stamp"],
                uuid=bytearray.fromhex(obj["uuid"]),
                offset=obj["offset"],
            )
        if "type" in obj and obj["type"] == "Update":
            return Update(
                clock_uuid=bytearray.fromhex(obj["clock_uuid"]),
                time_stamp=obj["time_stamp"],
                data=(
                    json.loads(obj["data"], cls=HoraoDecoder) if obj["data"] else None
                ),
                update_type=UpdateType(obj["update_type"]),
                writer=obj["writer"] if obj["writer"] else None,
                name=obj["name"] if obj["name"] else None,
            )
        if "type" in obj and obj["type"] == "ObservedRemovedSet":
            return ObservedRemovedSet(
                observed=(
                    json.loads(obj["observed"], cls=HoraoDecoder)
                    if obj["observed"]
                    else None
                ),
                observed_metadata=(
                    json.loads(obj["observed_metadata"], cls=HoraoDecoder)
                    if obj["observed_metadata"]
                    else None
                ),
                removed=(
                    json.loads(obj["removed"], cls=HoraoDecoder)
                    if obj["removed"]
                    else None
                ),
                removed_metadata=(
                    json.loads(obj["removed_metadata"], cls=HoraoDecoder)
                    if obj["removed_metadata"]
                    else None
                ),
                clock=(
                    json.loads(obj["clock"], cls=HoraoDecoder) if obj["clock"] else None
                ),
                listeners=(
                    json.loads(obj["listeners"], cls=HoraoDecoder)
                    if obj["listeners"]
                    else None
                ),
            )
        if "type" in obj and obj["type"] == "LastWriterWinsRegister":
            return LastWriterWinsRegister(
                name=json.loads(obj["name"], cls=HoraoDecoder),
                value=(
                    json.loads(obj["value"], cls=HoraoDecoder) if obj["value"] else None
                ),
                clock=(
                    json.loads(obj["clock"], cls=HoraoDecoder) if obj["clock"] else None
                ),
                last_update=obj["last_update"] if obj["last_update"] else None,
                last_writer=obj["last_writer"] if obj["last_writer"] else None,
                listeners=(
                    json.loads(obj["listeners"], cls=HoraoDecoder)
                    if obj["listeners"]
                    else None
                ),
            )
        if "type" in obj and obj["type"] == "LastWriterWinsMap":
            registers = {}
            for k, v in obj["registers"].items():
                registers[json.loads(k, cls=HoraoDecoder)] = json.loads(
                    v, cls=HoraoDecoder
                )
            return LastWriterWinsMap(
                names=(
                    json.loads(obj["names"], cls=HoraoDecoder) if obj["names"] else None
                ),
                listeners=(
                    json.loads(obj["listeners"], cls=HoraoDecoder)
                    if obj["listeners"]
                    else None
                ),
                registers=registers,
            )
        if "type" in obj and obj["type"] == "HardwareList":
            return HardwareList(items=json.loads(obj["hardware"], cls=HoraoDecoder))
        if "type" in obj and obj["type"] == "Port":
            return Port(
                serial_number=obj["serial_number"],
                model=obj["model"],
                number=obj["number"],
                mac=obj["mac"],
                status=DeviceStatus(obj["status"]),
                connected=obj["connected"],
                speed_gb=obj["speed_gb"],
            )
        if "type" in obj and obj["type"] == "NIC":
            return NIC(
                serial_number=obj["serial_number"],
                model=obj["model"],
                number=obj["number"],
                ports=json.loads(obj["ports"], cls=HoraoDecoder),
            )
        if "type" in obj and obj["type"] == "Switch":
            return Switch(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                layer=LinkLayer(obj["layer"]),
                switch_type=SwitchType(obj["switch_type"]),
                status=DeviceStatus(obj["status"]),
                managed=obj["managed"],
                lan_ports=json.loads(obj["lan_ports"], cls=HoraoDecoder),
                uplink_ports=(
                    json.loads(obj["uplink_ports"], cls=HoraoDecoder)
                    if obj["uplink_ports"]
                    else None
                ),
            )
        if "type" in obj and obj["type"] == "Router":
            return Router(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                router_type=RouterType(obj["router_type"]),
                status=DeviceStatus(obj["status"]),
                lan_ports=json.loads(obj["lan_ports"], cls=HoraoDecoder),
                wan_ports=(
                    json.loads(obj["wan_ports"], cls=HoraoDecoder)
                    if obj["wan_ports"]
                    else None
                ),
            )
        if "type" in obj and obj["type"] == "Firewall":
            return Firewall(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                status=DeviceStatus(obj["status"]),
                lan_ports=json.loads(obj["lan_ports"], cls=HoraoDecoder),
                wan_ports=(
                    json.loads(obj["wan_ports"], cls=HoraoDecoder)
                    if obj["wan_ports"]
                    else None
                ),
            )
        if "type" in obj and obj["type"] == "CPU":
            return CPU(
                serial_number=obj["serial_number"],
                model=obj["model"],
                number=obj["number"],
                clock_speed=obj["clock_speed"],
                cores=obj["cores"],
                features=obj["features"] if obj["features"] else None,
            )
        if "type" in obj and obj["type"] == "RAM":
            return RAM(
                serial_number=obj["serial_number"],
                model=obj["model"],
                number=obj["number"],
                size_gb=obj["size_gb"],
                speed_mhz=obj["speed_mhz"] if obj["speed_mhz"] else None,
            )
        if "type" in obj and obj["type"] == "Accelerator":
            return Accelerator(
                serial_number=obj["serial_number"],
                model=obj["model"],
                number=obj["number"],
                memory_gb=obj["memory_gb"],
                chip=obj["chip"] if obj["chip"] else None,
                clock_speed=obj["clock_speed"] if obj["clock_speed"] else None,
            )
        if "type" in obj and obj["type"] == "Disk":
            return Disk(
                serial_number=obj["serial_number"],
                model=obj["model"],
                number=obj["number"],
                size_gb=obj["size_gb"],
            )
        if "type" in obj and obj["type"] == "Server":
            return Server(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                cpus=json.loads(obj["cpus"], cls=HoraoDecoder),
                rams=json.loads(obj["rams"], cls=HoraoDecoder),
                nics=json.loads(obj["nics"], cls=HoraoDecoder),
                disks=(
                    json.loads(obj["disks"], cls=HoraoDecoder) if obj["disks"] else None
                ),
                accelerators=(
                    json.loads(obj["accelerators"], cls=HoraoDecoder)
                    if obj["accelerators"]
                    else None
                ),
                status=DeviceStatus(obj["status"]),
            )
        if "type" in obj and obj["type"] == "Module":
            return Module(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                cpus=json.loads(obj["cpus"], cls=HoraoDecoder),
                rams=json.loads(obj["rams"], cls=HoraoDecoder),
                nics=json.loads(obj["nics"], cls=HoraoDecoder),
                disks=(
                    json.loads(obj["disks"], cls=HoraoDecoder) if obj["disks"] else None
                ),
                accelerators=(
                    json.loads(obj["accelerators"], cls=HoraoDecoder)
                    if obj["accelerators"]
                    else None
                ),
                status=DeviceStatus(obj["status"]),
            )
        if "type" in obj and obj["type"] == "Node":
            return Node(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                modules=(
                    json.loads(obj["modules"], cls=HoraoDecoder)
                    if obj["modules"]
                    else None
                ),
            )
        if "type" in obj and obj["type"] == "Blade":
            return Blade(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                nodes=(
                    json.loads(obj["nodes"], cls=HoraoDecoder) if obj["nodes"] else None
                ),
            )
        if "type" in obj and obj["type"] == "Chassis":
            return Chassis(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                servers=(
                    json.loads(obj["servers"], cls=HoraoDecoder)
                    if obj["servers"]
                    else None
                ),
                blades=(
                    json.loads(obj["blades"], cls=HoraoDecoder)
                    if obj["blades"]
                    else None
                ),
            )
        if "type" in obj and obj["type"] == "Cabinet":
            return Cabinet(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                servers=(
                    json.loads(obj["servers"], cls=HoraoDecoder)
                    if obj["servers"]
                    else None
                ),
                chassis=(
                    json.loads(obj["chassis"], cls=HoraoDecoder)
                    if obj["chassis"]
                    else None
                ),
                switches=(
                    json.loads(obj["switches"], cls=HoraoDecoder)
                    if obj["switches"]
                    else None
                ),
            )
        if "type" in obj and obj["type"] == "DataCenter":
            return DataCenter(
                name=obj["name"],
                number=obj["number"],
                rows=json.loads(obj["rows"], cls=HoraoDecoder),
            )
        if "type" in obj and obj["type"] == "DataCenterNetwork":
            dcn = DataCenterNetwork(
                name=obj["name"],
                network_type=NetworkType(obj["network_type"]),
                high_speed_network=obj["hsn"],
            )
            for node in json.loads(obj["nodes"], cls=HoraoDecoder):
                dcn.add(node)
            dcn.links_from_graph(from_dict_of_dicts(json.loads(obj["graph"])))
            return dcn
        if "type" in obj and obj["type"] == "LogicalInfrastructure":
            infrastructure = {}
            for k, v in obj["infrastructure"].items():
                infrastructure[json.loads(k, cls=HoraoDecoder)] = json.loads(
                    v, cls=HoraoDecoder
                )
            constraints = {}
            for k, v in obj["constraints"].items():
                constraints[json.loads(k, cls=HoraoDecoder)] = json.loads(
                    v, cls=HoraoDecoder
                )
            claims = (
                json.loads(obj["claims"], cls=HoraoDecoder) if obj["claims"] else None
            )
            return LogicalInfrastructure(
                infrastructure=infrastructure,
                constraints=constraints,
                claims=claims,
            )

        return obj
