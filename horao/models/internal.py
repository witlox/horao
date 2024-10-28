from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from hashlib import sha256
from typing import Any, Callable, Hashable, Optional, Protocol, runtime_checkable
from uuid import uuid4


@dataclass
class LogicalClock:
    """Lamport logical clock."""

    time_stamp: float = field(default=datetime.timestamp(datetime.now(tz=timezone.utc)))
    uuid: bytes = field(default_factory=lambda: uuid4().bytes)

    def read(self) -> float:
        """
        Return the current timestamp.
        :return: unix timestamp
        """
        return self.time_stamp

    def update(self) -> float:
        """
        Update the clock and return the current time stamp.
        :return: unix timestamp (clock value set)
        """
        self.time_stamp = datetime.timestamp(datetime.now(tz=timezone.utc))
        return self.time_stamp

    @staticmethod
    def is_later(time_stamp: float, other_time_stamp: float) -> bool:
        """
        Compare two timestamps, True if time_stamp > other_time_stamp.
        :param time_stamp: unix timestamp
        :param other_time_stamp: unix timestamp
        :return: bool
        """
        return time_stamp > other_time_stamp

    @staticmethod
    def are_concurrent(time_stamp: float, other_time_stamp: float) -> bool:
        """
        Compare two timestamps, True if not time_stamp > other_time_stamp and not other_time_stamp > time_stamp.
        :param time_stamp: unix timestamp
        :param other_time_stamp: unix timestamp
        :return: bool
        """
        return not (time_stamp > other_time_stamp) and not (
            other_time_stamp > time_stamp
        )

    @staticmethod
    def compare(time_stamp: float, other_time_stamp: float) -> int:
        """
        Compare two timestamps, returns 1 if time_stamp is later than other_time_stamp; -1 if other_time_stamp is later than
        time_stamp; and 0 if they are concurrent/incomparable.
        :param time_stamp: unix timestamp
        :param other_time_stamp: unix timestamp
        :return: int
        """
        if time_stamp > other_time_stamp:
            return 1
        elif other_time_stamp > time_stamp:
            return -1
        return 0

    def __repr__(self) -> str:
        return f"ScalarClock(time_stamp={self.time_stamp}, uuid={self.uuid.hex()})"


class UpdateType(Enum):
    Observed = auto()
    Removed = auto()


@dataclass
class Update:
    """Default class for encoding delta states."""

    clock_uuid: bytes
    time_stamp: float
    data: Optional[Hashable]
    update_type: Optional[UpdateType]
    writer: Optional[Hashable]
    name: Optional[Hashable]

    def sha256(self) -> bytes:
        return sha256(f"{hash(self)}".encode("utf-8")).digest()

    def __hash__(self):
        return hash(
            (
                self.clock_uuid,
                self.time_stamp,
                self.data,
                self.update_type,
                self.writer,
                self.name,
            )
        )

    def __repr__(self) -> str:
        return (
            f"Update(clock_uuid={self.clock_uuid.hex()}, "
            f"time_stamp={self.time_stamp}, "
            f"data={self.data}, "
            f"update_type={self.update_type}, "
            f"writer={self.writer}), "
            f"name={self.name})"
        )


@runtime_checkable
class CRDT(Protocol):
    """Protocol showing what CRDTs must do."""

    clock: LogicalClock

    def read(self) -> Any:
        """
        Return the eventually consistent data view.
        :return: Any
        """
        ...

    def update(self, state_update: Update) -> CRDT:
        """
        Apply an update. Should call self.invoke_listeners after validating the state_update.
        :param state_update: update to apply
        :return: self (monad)
        """
        ...

    def checksum(
        self, /, *, from_time_stamp: float = None, until_time_stamp: float = None
    ) -> tuple[int]:
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
        from_time_stamp: float = None,
        until_time_stamp: float = None,
    ) -> tuple[Update]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for resynchronization by
        replaying all updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[Update]
        """
        ...

    def get_merkle_tree(self) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a Merkle tree of history for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
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
    leaves = [update for update in history]
    leaf_ids = [leaf.sha256() for leaf in leaves]
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
