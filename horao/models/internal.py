from __future__ import annotations

import struct
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Hashable, Type, runtime_checkable, Protocol, Any, Callable
from uuid import uuid4

from packify import SerializableType, pack, unpack


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
class Update:
    """Default class for encoding delta states."""

    clock_uuid: bytes
    time_stamp: SerializableType
    data: Hashable

    def pack(self) -> bytes:
        """Serialize an Update."""
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
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        if len(data) < 12:
            raise ValueError("data must be at least 12 long")
        u, t, d = unpack(data, inject=inject)
        return Update(clock_uuid=u, time_stamp=t, data=d)

    def __repr__(self) -> str:
        return f"Update(clock_uuid={self.clock_uuid.hex()}, time_stamp={self.time_stamp}, data={self.data})"


@runtime_checkable
class CRDT(Protocol):
    """Protocol showing what CRDTs must do."""

    clock: ScalarClock

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes (encoded self)
        """
        ...

    @classmethod
    def unpack(cls, data: bytes, /, *, inject=None) -> CRDT:
        """
        Unpack the data bytes string into an instance.
        :param data: bytes
        :param inject: optional data to inject during unpacking
        :return: instance of self
        """
        ...

    def read(self, /, *, inject: dict = None) -> Any:
        """
        Return the eventually consistent data view.
        :param inject: optional data to inject during unpacking
        :return: Any
        """
        ...

    def update(self, state_update: Update, /, *, inject: dict = None) -> CRDT:
        """
        Apply an update. Should call self.invoke_listeners after validating the state_update.
        :param state_update: update to apply
        :param inject: optional data to inject during unpacking
        :return: self (monad)
        """
        ...

    def checksums(
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[Any]:
        """
        Returns any checksums for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[Any]
        """
        ...

    def history(
        self,
        /,
        *,
        from_time_stamp: Any = None,
        until_time_stamp: Any = None,
    ) -> tuple[Update]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for resynchronization by
        replaying all updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[Update]
        """
        ...

    def get_merkle_tree(self, /) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a Merkle tree of history for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        :param update_class: type of update to use
        :return: list[bytes, list[bytes], dict[bytes, bytes
        """
        ...

    def resolve_merkle_tree(self, tree: list[bytes, list[bytes]]) -> list[bytes]:
        """
        Accept a tree of form [root, leaves] from another node.
        Return the leaves that need to be resolved and merged for
        synchronization.
        :param tree: tree to resolve
        :return: list[bytes]
        """
        ...

    def add_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Adds a listener that is called on each update.
        :param listener: listener to add
        :return: None
        """
        ...

    def remove_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Removes a listener if it was previously added.
        :param listener: listener to remove
        :return: None
        """
        ...

    def invoke_listeners(self, state_update: Update) -> None:
        """
        Invokes all event listeners, passing them the state_update.
        :param state_update: update to pass to listeners
        :return: None
        """
        ...


def get_merkle_tree(crdt: CRDT) -> list[bytes | list[bytes] | dict[bytes, bytes]]:
    """
    Get a Merkle tree of the history of Updates of the form
    [root, [content_id for update in crdt.history()], {
    content_id: packed for update in crdt.history()}] where
    packed is the result of update.pack() and content_id is the
    sha256 of the packed update.
    :param crdt: CRDT to get the Merkle tree from
    :return: list[bytes | list[bytes] | dict[bytes, bytes
    """
    history = crdt.history()
    leaves = [update.pack() for update in history]
    leaf_ids = [sha256(leaf).digest() for leaf in leaves]
    history = {leaf_id: leaf for leaf_id, leaf in zip(leaf_ids, leaves)}
    leaf_ids.sort()
    root = sha256(b"".join(leaf_ids)).digest()
    return [root, leaf_ids, history]


def resolve_merkle_tree(crdt: CRDT, tree: list[bytes, list[bytes]]) -> list[bytes]:
    """
    Accept a merkle tree of form [root, leaves] from another node.
    Return the leaves that need to be resolved and merged for
    synchronization.
    :param crdt: CRDT to resolve the tree for
    :param tree: tree to resolve
    :return: list[bytes]
    :raises ValueError: invalid tree
    """
    if len(tree) < 2:
        raise ValueError("tree has no (or only one) leaves")
    local_history = get_merkle_tree(crdt)
    if local_history[0] == tree[0]:
        return []
    return [leaf for leaf in tree[1] if leaf not in local_history[1]]
