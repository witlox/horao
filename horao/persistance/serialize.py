# -*- coding: utf-8 -*-#
import json
from datetime import date, datetime

from networkx.readwrite import json_graph

from horao.conceptual.crdt import (
    CRDTList,
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
from horao.physical.hardware import Hardware, HardwareList
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
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, set):
            return {"type": "Set", "content": list(obj)}
        if isinstance(obj, LogicalClock):
            return {
                "type": "LogicalClock",
                "time_stamp": obj.time_stamp,
                "uuid": obj.uuid.hex(),
                "offset": obj.offset,
            }
        if isinstance(obj, Update):
            result = {
                "type": "Update",
                "clock_uuid": obj.clock_uuid.hex(),
                "time_stamp": obj.time_stamp,
            }
            if obj.data:
                result["data"] = obj.data
            if obj.update_type:
                result["update_type"] = obj.update_type.value
            if obj.writer:
                result["writer"] = obj.writer
            if obj.name:
                result["name"] = obj.name
            return result
        if isinstance(obj, ObservedRemovedSet):
            result = {
                "type": "ObservedRemovedSet",
            }
            if obj.observed:
                result["observed"] = obj.observed
            if obj.observed_metadata:
                result["observed_metadata"] = obj.observed_metadata
            if obj.removed:
                result["removed"] = obj.removed
            if obj.removed_metadata:
                result["removed_metadata"] = obj.removed_metadata
            if obj.clock:
                result["clock"] = obj.clock
            if obj.listeners:
                result["listeners"] = obj.listeners
            return result
        if isinstance(obj, LastWriterWinsRegister):
            result = {
                "type": "LastWriterWinsRegister",
                "name": obj.name,
            }
            if obj.value:
                result["value"] = obj.value
            if obj.clock:
                result["clock"] = obj.clock
            if obj.last_update:
                result["last_update"] = obj.last_update
            if obj.last_writer:
                result["last_writer"] = obj.last_writer
            if obj.listeners:
                result["listeners"] = obj.listeners
            return result
        if isinstance(obj, LastWriterWinsMap):
            result = {"type": "LastWriterWinsMap"}
            if obj.names:
                result["names"] = obj.names
            if obj.registers:
                result["registers"] = obj.registers
            if obj.listeners:
                result["listeners"] = obj.listeners
            return result
        if isinstance(obj, CRDTList):
            return {
                "type": "CRDTList",
                "hardware": json.dumps(obj.hardware, cls=HoraoEncoder),
            }
        if isinstance(obj, Hardware):
            return {
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
            }
        if isinstance(obj, HardwareList):
            return {
                "type": "HardwareList",
                "hardware": json.dumps(obj.hardware, cls=HoraoEncoder),
            }
        if isinstance(obj, Port):
            return {
                "type": "Port",
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "mac": obj.mac,
                "status": obj.status.value,
                "connected": obj.connected,
                "speed_gb": obj.speed_gb,
            }
        if isinstance(obj, NIC):
            return {
                "type": "NIC",
                "serial_number": obj.serial_number,
                "name": obj.name,
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
                    else []
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
                    json.dumps(obj.wan_ports, cls=HoraoEncoder) if obj.wan_ports else []
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
                    json.dumps(obj.wan_ports, cls=HoraoEncoder) if obj.wan_ports else []
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
                "features": obj.features if obj.features else "",
            }
        if isinstance(obj, RAM):
            return {
                "type": "RAM",
                "serial_number": obj.serial_number,
                "model": obj.model,
                "number": obj.number,
                "size_gb": obj.size_gb,
                "speed_mhz": obj.speed_mhz if obj.speed_mhz else 0,
            }
        if isinstance(obj, Accelerator):
            return {
                "type": "Accelerator",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "memory_gb": obj.memory_gb,
                "chip": obj.chip if obj.chip else "",
                "clock_speed": obj.clock_speed if obj.clock_speed else 0,
            }
        if isinstance(obj, Disk):
            return {
                "type": "Disk",
                "serial_number": obj.serial_number,
                "name": obj.name,
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
                "accelerators": json.dumps(obj.accelerators, cls=HoraoEncoder),
                "disks": json.dumps(obj.disks, cls=HoraoEncoder),
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
                "accelerators": json.dumps(obj.accelerators, cls=HoraoEncoder),
                "disks": json.dumps(obj.disks, cls=HoraoEncoder),
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
                    json.dumps(obj.modules, cls=HoraoEncoder) if obj.modules else []
                ),
            }
        if isinstance(obj, Blade):
            return {
                "type": "Blade",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "nodes": json.dumps(obj.nodes, cls=HoraoEncoder) if obj.nodes else [],
            }
        if isinstance(obj, Chassis):
            return {
                "type": "Chassis",
                "serial_number": obj.serial_number,
                "name": obj.name,
                "model": obj.model,
                "number": obj.number,
                "servers": (
                    json.dumps(obj.servers, cls=HoraoEncoder) if obj.servers else []
                ),
                "blades": (
                    json.dumps(obj.blades, cls=HoraoEncoder) if obj.blades else []
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
                    json.dumps(obj.servers, cls=HoraoEncoder) if obj.servers else []
                ),
                "chassis": (
                    json.dumps(obj.chassis, cls=HoraoEncoder) if obj.chassis else []
                ),
                "switches": (
                    json.dumps(obj.switches, cls=HoraoEncoder) if obj.switches else []
                ),
            }
        if isinstance(obj, DataCenter):
            result = {
                "type": "DataCenter",
                "name": obj.name,
                "number": obj.number,
            }
            for row in obj.rows:
                result["rows"] = json.dumps(row, cls=HoraoEncoder)
            return result
        if isinstance(obj, DataCenterNetwork):
            return {
                "type": "DataCenterNetwork",
                "name": obj.name,
                "network_type": (
                    "data"
                    if obj.network_type == NetworkType.Data
                    else (
                        "control"
                        if obj.network_type == NetworkType.Control
                        else "management"
                    )
                ),
                "graph": json_graph.adjacency_data(obj.graph),
            }
        if isinstance(obj, LogicalInfrastructure):
            result = {
                "type": "LogicalInfrastructure",
                "infrastructure": {},
                "constraints": {},
                "claims": [],
            }
            for k, v in obj.infrastructure.items():
                result["infrastructure"][k] = json.dumps(v, cls=HoraoEncoder)
            for k, v in obj.constraints.items():
                result["constraints"][k] = json.dumps(v, cls=HoraoEncoder)
            for c in obj.claims:
                result["claims"].append(c)
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
            return set(obj["content"])
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
                data=obj["data"] if "data" in obj else None,
                update_type=(
                    UpdateType(obj["update_type"]) if "update_type" in obj else None
                ),
                writer=obj["writer"] if "writer" in obj else None,
                name=obj["name"] if "name" in obj else None,
            )
        if "type" in obj and obj["type"] == "ObservedRemovedSet":
            return ObservedRemovedSet(
                observed=obj["observed"] if "observed" in obj else None,
                observed_metadata=(
                    obj["observed_metadata"] if "observed_metadata" in obj else None
                ),
                removed=obj["removed"] if "removed" in obj else None,
                removed_metadata=(
                    obj["removed_metadata"] if "removed_metadata" in obj else None
                ),
                clock=obj["clock"] if "clock" in obj else None,
                listeners=obj["listeners"] if "listeners" in obj else None,
            )
        if "type" in obj and obj["type"] == "LastWriterWinsRegister":
            return LastWriterWinsRegister(
                name=obj["name"],
                value=obj["value"] if "value" in obj else None,
                clock=obj["clock"] if "clock" in obj else None,
                last_update=obj["last_update"] if "last_update" in obj else None,
                last_writer=obj["last_writer"] if "last_writer" in obj else None,
                listeners=obj["listeners"] if "listeners" in obj else None,
            )
        if "type" in obj and obj["type"] == "LastWriterWinsMap":
            return LastWriterWinsMap(
                names=obj["names"] if "names" in obj else None,
                registers=obj["registers"] if "registers" in obj else None,
                listeners=obj["listeners"] if "listeners" in obj else None,
            )
        if "type" in obj and obj["type"] == "CRDTList":
            return CRDTList(json.loads(obj["hardware"], cls=HoraoDecoder))
        if "type" in obj and obj["type"] == "Hardware":
            return Hardware(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
            )
        if "type" in obj and obj["type"] == "HardwareList":
            return HardwareList(json.loads(obj["hardware"], cls=HoraoDecoder))
        if "type" in obj and obj["type"] == "Port":
            return Port(
                serial_number=obj["serial_number"],
                name=obj["name"],
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
                name=obj["name"],
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
                uplink_ports=json.loads(obj["uplink_ports"], cls=HoraoDecoder),
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
                wan_ports=json.loads(obj["wan_ports"], cls=HoraoDecoder),
            )
        if "type" in obj and obj["type"] == "Firewall":
            return Firewall(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                status=DeviceStatus(obj["status"]),
                lan_ports=json.loads(obj["lan_ports"], cls=HoraoDecoder),
                wan_ports=json.loads(obj["wan_ports"], cls=HoraoDecoder),
            )
        if "type" in obj and obj["type"] == "CPU":
            return CPU(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                clock_speed=obj["clock_speed"],
                cores=obj["cores"],
                features=obj["features"],
            )
        if "type" in obj and obj["type"] == "RAM":
            return RAM(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                size_gb=obj["size_gb"],
                speed_mhz=obj["speed_mhz"],
            )
        if "type" in obj and obj["type"] == "Accelerator":
            return Accelerator(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                memory_gb=obj["memory_gb"],
                chip=obj["chip"],
                clock_speed=obj["clock_speed"],
            )
        if "type" in obj and obj["type"] == "Disk":
            return Disk(
                serial_number=obj["serial_number"],
                name=obj["name"],
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
                accelerators=json.loads(obj["accelerators"], cls=HoraoDecoder),
                disks=json.loads(obj["disks"], cls=HoraoDecoder),
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
                accelerators=json.loads(obj["accelerators"], cls=HoraoDecoder),
                disks=json.loads(obj["disks"], cls=HoraoDecoder),
                status=DeviceStatus(obj["status"]),
            )
        if "type" in obj and obj["type"] == "Node":
            return Node(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                modules=json.loads(obj["modules"], cls=HoraoDecoder),
            )
        if "type" in obj and obj["type"] == "Blade":
            return Blade(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                nodes=json.loads(obj["nodes"], cls=HoraoDecoder),
            )
        if "type" in obj and obj["type"] == "Chassis":
            return Chassis(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                servers=json.loads(obj["servers"], cls=HoraoDecoder),
                blades=json.loads(obj["blades"], cls=HoraoDecoder),
            )
        if "type" in obj and obj["type"] == "Cabinet":
            return Cabinet(
                serial_number=obj["serial_number"],
                name=obj["name"],
                model=obj["model"],
                number=obj["number"],
                servers=json.loads(obj["servers"], cls=HoraoDecoder),
                chassis=json.loads(obj["chassis"], cls=HoraoDecoder),
                switches=json.loads(obj["switches"], cls=HoraoDecoder),
            )
        if "type" in obj and obj["type"] == "LogicalInfrastructure":
            return LogicalInfrastructure(
                obj["infrastructure"], obj["constraints"], obj["claims"]
            )
        if "type" in obj and obj["type"] == "DataCenter":
            return DataCenter(
                obj["name"], obj["number"], json.loads(obj["rows"], cls=HoraoDecoder)
            )
        if "type" in obj and obj["type"] == "DataCenterNetwork":
            return DataCenterNetwork(
                obj["name"],
                (
                    NetworkType.Data
                    if obj["network_type"] == "data"
                    else (
                        NetworkType.Control
                        if obj["network_type"] == "control"
                        else NetworkType.Management
                    )
                ),
                json_graph.adjacency_graph(obj["graph"]),
            )

        return obj
