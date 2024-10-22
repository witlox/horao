from __future__ import annotations

import struct
from abc import ABC
from dataclasses import dataclass, field
from types import NoneType

from packify import SerializableType, pack, unpack

from .protocols import Data


@dataclass
class String:
    value: str

    def __to_tuple__(self) -> tuple:
        return self.__class__.__name__, self.value

    def __hash__(self) -> int:
        return hash(self.__to_tuple__())

    def __eq__(self, other: Data) -> bool:
        return type(self) == type(other) and hash(self) == hash(other)

    def __ne__(self, other: Data) -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: Data) -> bool:
        return self.value > other.value

    def __ge__(self, other: Data) -> bool:
        return self.value >= other.value

    def __lt__(self, other: Data) -> bool:
        return other.value > self.value

    def __le__(self, other: Data) -> bool:
        return other.value >= self.value

    def pack(self) -> bytes:
        data = bytes(self.value, "utf-8")
        return struct.pack(f"!{len(data)}s", data)

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> String:
        return cls(str(struct.unpack(f"!{len(data)}s", data)[0], "utf-8"))


class Bytes(String):
    value: bytes

    def __init__(self, value: bytes) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Bytes(value={self.value.hex()})"

    def pack(self) -> bytes:
        return struct.pack(f"!{len(self.value)}s", self.value)

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Bytes:
        return cls(struct.unpack(f"!{len(data)}s", data)[0])


class ComplexType:
    value: SerializableType
    uuid: bytes
    parent_uuid: bytes
    visible: bool

    def __init__(
        self,
        value: SerializableType,
        uuid: bytes,
        parent_uuid: bytes,
        visible: bool = True,
    ) -> None:
        self.value = value
        self.uuid = uuid
        self.parent_uuid = parent_uuid
        self.visible = visible

    def __to_tuple__(self) -> tuple:
        return (
            self.__class__.__name__,
            self.value,
            self.uuid,
            self.parent_uuid,
            self.visible,
        )

    def __repr__(self) -> str:
        return (
            f"ComplexType(value={self.value}, uuid={self.uuid.hex()}, "
            + f"parent_uuid={self.parent_uuid.hex()}, visible={self.visible})"
        )

    def __hash__(self) -> int:
        return hash(self.__to_tuple__())

    def __eq__(self, other: ComplexType) -> bool:
        return type(self) == type(other) and hash(self) == hash(other)

    def __ne__(self, other: ComplexType) -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: ComplexType) -> bool:
        return self.__to_tuple__() > other.__to_tuple__()

    def __ge__(self, other: ComplexType) -> bool:
        return self.__to_tuple__() >= other.__to_tuple__()

    def __lt__(self, other: ComplexType) -> bool:
        return self.__to_tuple__() < other.__to_tuple__()

    def __le__(self, other: ComplexType) -> bool:
        return self.__to_tuple__() <= other.__to_tuple__()

    def pack(self) -> bytes:
        return pack([self.value, self.uuid, self.parent_uuid, int(self.visible)])

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> ComplexType:
        value, uuid, parent_uuid, visible = (
            unpack(data, inject={**globals(), **inject})
            if inject
            else unpack(data, inject={**globals()})
        )
        return cls(
            value=value, uuid=uuid, parent_uuid=parent_uuid, visible=bool(visible)
        )


class Number(float):
    value: int | float

    def __to_tuple__(self) -> tuple:
        return self.__class__.__name__, self.value

    def __hash__(self) -> int:
        return hash(self.__to_tuple__())


class Float(Number):
    value: float

    def __init__(self, value: float) -> None:
        self.value = value

    def pack(self) -> bytes:
        return struct.pack("!d", self.value)

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Float:
        return cls(struct.unpack("!d", data)[0])


class FractionallyIndexedArrayItem:
    value: SerializableType
    index: Float
    uuid: bytes

    def __init__(
        self, value: SerializableType, index: Float | Float, uuid: bytes
    ) -> None:
        self.value = value
        self.index = index if isinstance(index, Float) else Float(index)
        self.uuid = uuid

    def __hash__(self) -> int:
        return hash((self.value, self.index, self.uuid))

    def __repr__(self) -> str:
        return f"FractionallyIndexedArrayItem(value={self.value}, index={self.index.value}, uuid={self.uuid.hex()}"

    def __eq__(self, other) -> bool:
        return type(other) == type(self) and hash(self) == hash(other)

    def __ne__(self, other) -> bool:
        return not (self == other)

    def __gt__(self, other) -> bool:
        return (self.value, self.index, self.uuid) > (
            other.value,
            other.index,
            other.uuid,
        )

    def __ge__(self, other) -> bool:
        return (self.value, self.index, self.uuid) >= (
            other.value,
            other.index,
            other.uuid,
        )

    def __lt__(self, other) -> bool:
        return (self.value, self.index, self.uuid) < (
            other.value,
            other.index,
            other.uuid,
        )

    def __le__(self, other) -> bool:
        return (self.value, self.index, self.uuid) <= (
            other.value,
            other.index,
            other.uuid,
        )

    def pack(self) -> bytes:
        return pack([self.value, self.index, self.uuid])

    @classmethod
    def unpack(
        cls, data: bytes, /, *, inject: dict = None
    ) -> FractionallyIndexedArrayItem:
        value, index, uuid = (
            unpack(data, inject={**globals(), **inject})
            if inject
            else unpack(data, inject={**globals()})
        )
        return cls(
            value=value,
            index=index,
            uuid=uuid,
        )


class Integer(Number):
    value: int

    def __init__(self, value: int) -> None:
        self.value = value

    def pack(self) -> bytes:
        return struct.pack("!i", self.value)

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Integer:
        return cls(struct.unpack("!i", data)[0])


class ReplicatedGrowableArrayItem(String):
    value: SerializableType
    time_stamp: SerializableType
    writer: SerializableType

    def __init__(
        self,
        value: SerializableType,
        time_stamp: SerializableType,
        writer: SerializableType,
    ) -> None:
        self.value = value
        self.time_stamp = time_stamp
        self.writer = writer

    def pack(self) -> bytes:
        """
        Pack instance to bytes.
        :return: self as bytes
        """
        return pack([self.value, self.time_stamp, self.writer])

    @classmethod
    def unpack(
        cls, data: bytes, /, *, inject: dict = None
    ) -> ReplicatedGrowableArrayItem:
        """
        Unpack a ReplicatedGrowableArrayItem from bytes.
        :param data: raw bytes
        :param inject: optional data to inject during unpacking
        :return: ReplicatedGrowableArrayItem instance
        """
        v, t, w = (
            unpack(data, inject={**globals(), **inject})
            if inject
            else unpack(data, inject={**globals()})
        )
        return cls(value=v, time_stamp=t, writer=w)

    def __repr__(self) -> str:
        return f"ReplicatedGrowableArrayItem(value={self.value}, ts={self.time_stamp}, writer={self.writer})"


@dataclass
class Nothing:
    """Use in removing registers from the LWWMap by setting them to a None value."""

    value: NoneType = field(default=None)

    def __hash__(self) -> int:
        return hash(None)

    def __eq__(self, other) -> bool:
        return type(self) == type(other)

    def __ne__(self, other) -> bool:
        return not (self == other)

    def __gt__(self, other) -> bool:
        return False

    def __ge__(self, other) -> bool:
        return False

    def __lt__(self, other) -> bool:
        return False

    def __le__(self, other) -> bool:
        return False

    @staticmethod
    def pack() -> bytes:
        return b""

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Nothing:
        return cls()
