import json
from datetime import datetime, date

from horao.conceptual.crdt import (
    ObservedRemovedSet,
    LastWriterWinsRegister,
    LastWriterWinsMap,
)
from horao.conceptual.support import LogicalClock, Update, UpdateType


class HoraoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, set):
            return {"type": "set", "content": list(obj)}
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
                result["update_type"] = (
                    "observed" if obj.update_type == UpdateType.Observed else "removed"
                )
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
        return json.JSONEncoder.default(self, obj)


class HoraoDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if "date" in obj:
            return datetime.strptime(obj["date"], "%Y-%m-%d")
        if "type" in obj and obj["type"] == "set":
            return set(obj["content"])
        if "type" in obj and obj["type"] == "LogicalClock":
            return LogicalClock(
                obj["time_stamp"], bytearray.fromhex(obj["uuid"]), obj["offset"]
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

        return obj
