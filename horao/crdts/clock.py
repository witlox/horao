from __future__ import annotations

import struct
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ScalarClock:
    """Lamport logical scalar clock."""

    counter: int = field(default=1)
    uuid: bytes = field(default_factory=lambda: uuid4().bytes)
    default_time_stamp: int = field(default=0)

    def read(self) -> int:
        """
        Return the current timestamp.
        :return: int
        """
        return self.counter

    def update(self, data: int) -> int:
        """
        Update the clock and return the current time stamp.
        :param data: int (new clock value)
        :return: int (clock value set)
        :raises TypeError: data is not an int
        """
        if type(data) is not int:
            raise TypeError("data must be int")

        if data >= self.counter:
            self.counter = data + 1

        return self.counter

    @staticmethod
    def is_later(time_stamp: int, other_time_stamp: int) -> bool:
        """
        Compare two timestamps, True if time_stamp > other_time_stamp.
        :param time_stamp: int
        :param other_time_stamp: int
        :return: bool
        """
        return time_stamp > other_time_stamp

    @staticmethod
    def are_concurrent(time_stamp: int, other_time_stamp: int) -> bool:
        """
        Compare two timestamps, True if not time_stamp > other_time_stamp and not other_time_stamp > time_stamp.
        :param time_stamp: int
        :param other_time_stamp: int
        :return: bool
        """
        return not (time_stamp > other_time_stamp) and not (
            other_time_stamp > time_stamp
        )

    @staticmethod
    def compare(time_stamp: int, other_time_stamp: int) -> int:
        """
        Compare two timestamps, returns 1 if time_stamp is later than other_time_stamp; -1 if other_time_stamp is later than
        time_stamp; and 0 if they are concurrent/incomparable.
        :param time_stamp: int
        :param other_time_stamp: int
        :return: int
        """
        if time_stamp > other_time_stamp:
            return 1
        elif other_time_stamp > time_stamp:
            return -1
        return 0

    def pack(self) -> bytes:
        """
        Packs the clock into bytes.
        :return: bytes
        """
        return struct.pack(f"!I{len(self.uuid)}s", self.counter, self.uuid)

    @classmethod
    def unpack(cls, data: bytes, inject: dict = None) -> ScalarClock:
        """
        Unpacks a clock from bytes.
        :param data: bytes
        :param inject: optional injectable data
        :return: ScalarClock
        :raises ValueError: data is not at least 5 bytes
        """
        if len(data) < 5:
            raise ValueError("data must be at least 5 bytes")

        return cls(*struct.unpack(f"!I{len(data)-4}s", data))

    def __repr__(self) -> str:
        return (
            f"ScalarClock(counter={self.counter}, uuid={self.uuid.hex()}"
            + f", default_ts={self.default_time_stamp})"
        )


@dataclass
class StringClock:
    """Implements a logical clock using strings."""

    counter: str = field(default="0")
    uuid: bytes = field(default=b"1234567890")
    default_time_stamp: str = field(default="")

    def read(self) -> str:
        """
        Return the current timestamp.
        :return: str
        """
        return self.counter

    def update(self, data: str) -> str:
        """
        Update the clock and return the current time stamp.
        :param data: str (new clock value)
        :return: str (clock value set)
        """
        if len(data) >= len(self.counter):
            self.counter = data + "1"

        return self.counter

    @staticmethod
    def is_later(time_stamp: str, other_time_stamp: str) -> bool:
        """
        True if len(time_stamp) > len(other_time_stamp).
        :param time_stamp: str
        :param other_time_stamp: str
        :return: bool
        """
        return len(time_stamp) > len(other_time_stamp)

    @staticmethod
    def are_concurrent(time_stamp: str, other_time_stamp: str) -> bool:
        """
        True if len(time_stamp) == len(other_time_stamp).
        :param time_stamp: str
        :param other_time_stamp: str
        :return: bool
        """
        return len(time_stamp) == len(other_time_stamp)

    @staticmethod
    def compare(time_stamp: str, other_time_stamp: str) -> int:
        """
        1 if time_stamp is later than other_time_stamp; -1 if other_time_stamp is later than
        time_stamp; and 0 if they are concurrent/incomparable.
        :param time_stamp: str
        :param other_time_stamp: str
        :return: int
        """
        if len(time_stamp) > len(other_time_stamp):
            return 1
        elif len(other_time_stamp) > len(time_stamp):
            return -1
        return 0

    def pack(self) -> bytes:
        """
        clock into bytes.
        :return: bytes
        """
        return bytes(self.counter, "utf-8") + b"_" + self.uuid

    @classmethod
    def unpack(cls, data: bytes, inject=None) -> StringClock:
        """
        Unpacks a clock from bytes.
        :param data: bytes
        :param inject: optional injectable data
        :return: StringClock
        """
        if inject is None:
            inject = {}
        assert len(data) >= 5, "data must be at least 5 bytes"

        counter, _, uuid = data.partition(b"_")

        return cls(counter=str(counter, "utf-8"), uuid=uuid)

    @staticmethod
    def serialize_time_stamp(time_stamp: str) -> bytes:
        """
        Serialize a time_stamp.
        :param time_stamp: str
        :return: time_stamp as bytes
        """
        return bytes(time_stamp, "utf-8")

    @staticmethod
    def deserialize_time_stamp(time_stamp: bytes, /, *, inject=None) -> str:
        """
        Deserialize a time_stamp.
        :param time_stamp: bytes
        :param inject: optional injectable data
        :return: time_stamp as str
        """
        if inject is None:
            inject = {}
        return str(time_stamp, "utf-8")
