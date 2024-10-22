from __future__ import annotations

from typing import Any, Callable, Protocol, Type, runtime_checkable

from packify import SerializableType

from horao.crdts.update import Update


@runtime_checkable
class Clock(Protocol):
    """Protocol showing what a clock must do."""

    uuid: bytes
    default_time_stamp: SerializableType

    def read(self, /, *, inject=None) -> SerializableType:
        """
        Return the current timestamp.
        :param inject: optional data to inject during unpacking
        :return: SerializableType
        """
        ...

    def update(self, data: SerializableType = None) -> SerializableType:
        """
        Update the clock and return the current time stamp.
        :param data: new clock value
        :return: clock value set
        """
        ...

    @staticmethod
    def is_later(
        time_stamp: SerializableType, other_time_stamp: SerializableType
    ) -> bool:
        """
        True if time_stamp > other_time_stamp.
        :param time_stamp: SerializableType
        :param other_time_stamp: SerializableType
        :return: bool
        """
        ...

    @staticmethod
    def are_concurrent(
        time_stamp: SerializableType, other_time_stamp: SerializableType
    ) -> bool:
        """
        True if not time_stamp > other_time_stamp and not other_time_stamp > time_stamp.
        :param time_stamp: SerializableType
        :param other_time_stamp: SerializableType
        :return: bool
        """
        ...

    @staticmethod
    def compare(
        time_stamp: SerializableType, other_time_stamp: SerializableType
    ) -> int:
        """
        1 if time_stamp is later than other_time_stamp; -1 if other_time_stamp is later than
        time_stamp; and 0 if they are concurrent/incomparable.
        :param time_stamp: SerializableType
        :param other_time_stamp: SerializableType
        :return: int
        """
        ...

    def pack(self) -> bytes:
        """
        Pack the clock into bytes.
        :return: bytes (encoded self)
        """
        ...

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Clock:
        """
        Unpack a clock from bytes.
        :param data: bytes
        :param inject: optional data to inject during unpacking
        :return: Clock
        """
        ...


@runtime_checkable
class CRDT(Protocol):
    """Protocol showing what CRDTs must do."""

    clock: Clock

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
        update_class: Type[Update] = None,
    ) -> tuple[Update]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for resynchronization by
        replaying all updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :param update_class: type of update to use
        :return: tuple[Update]
        """
        ...

    def get_merkle_tree(
        self, /, *, update_class: Type[Update]
    ) -> list[bytes, list[bytes], dict[bytes, bytes]]:
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


@runtime_checkable
class List(Protocol):
    def index(self, item: SerializableType, _start: int = 0, _stop: int = -1) -> int:
        """
        Returns the int index of the item in the list returned by
        read().
        :param item: item to find
        :param _start: start index
        :param _stop: stop index
        :return: int
        :raises ValueError: item not in list
        """
        ...

    def append(
        self,
        item: SerializableType,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update],
    ) -> Update:
        """
        Creates, applies, and returns an update_class that appends
        the item to the end of the list returned by read().
        :param item: item to append
        :param writer: writer of the update
        :param update_class: type of update to use
        :return: Update
        """
        ...

    def remove(
        self, index: int, writer: SerializableType, /, *, update_class: Type[Update]
    ) -> Update:
        """
        Creates, applies, and returns an update_class that removes
        the item at the index in the list returned by read().
        :param index: index of the item to remove
        :param writer: writer of the update
        :param update_class: type of update to use
        :return: Update
        :raises ValueError: index out of bounds
        """
        ...


@runtime_checkable
class Data(Protocol):
    """Protocol for values that can be written to a LWWRegister,
    included in a GSet or ORSet, or be used as the key for a LWWMap.
    Can also be packed, unpacked, and compared.
    """

    value: Any

    def __hash__(self) -> int:
        """Data type must be hashable."""
        ...

    def __eq__(self, other) -> bool:
        """Data type must be comparable."""
        ...

    def __ne__(self, other) -> bool:
        """Data type must be comparable."""
        ...

    def __gt__(self, other) -> bool:
        """Data type must be comparable."""
        ...

    def __ge__(self, other) -> bool:
        """Data type must be comparable."""
        ...

    def __lt__(self, other) -> bool:
        """Data type must be comparable."""
        ...

    def __le__(self, other) -> bool:
        """Data type must be comparable."""
        ...

    def pack(self) -> bytes:
        """Package value into bytes."""
        ...

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Data:
        """Unpack value from bytes."""
        ...
