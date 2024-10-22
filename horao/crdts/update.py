from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable

from packify import SerializableType, pack, unpack


@dataclass
class Update:
    """Default class for encoding delta states."""

    clock_uuid: bytes
    time_stamp: SerializableType
    data: Hashable

    def pack(self) -> bytes:
        """Serialize a Update."""
        return pack(
            [
                self.clock_uuid,
                self.time_stamp,
                self.data,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject=None) -> Update:
        """
        Deserialize Update. Packable accessible from the inject dict.
        :param data: serialized Update needing unpacking
        :param inject: optional data to inject during unpacking
        :return: None
        :raises ValueError: data of wrong length
        """
        if inject is None:
            inject = {}
        if len(data) < 12:
            raise ValueError("data must be at least 12 long")
        u, t, d = unpack(data, inject=inject)
        return Update(clock_uuid=u, time_stamp=t, data=d)

    def __repr__(self) -> str:
        return f"Update(clock_uuid={self.clock_uuid.hex()}, time_stamp={self.time_stamp}, data={self.data})"
