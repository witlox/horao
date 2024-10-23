from __future__ import annotations

from binascii import crc32
from typing import Any, Callable, Type

from packify import SerializableType, pack, unpack

from .clock import ScalarClock
from .helpers import get_merkle_tree, resolve_merkle_tree
from .protocols import Clock
from .update import Update


class MultiValueRegister:
    """Implements the Multi-Value Register CRDT."""

    name: SerializableType
    values: list[SerializableType]
    clock: Clock
    last_update: Any
    listeners: list[Callable]

    def __init__(
        self,
        name: SerializableType,
        values=None,
        clock: Clock = None,
        last_update: Any = None,
        listeners: list[Callable] = None,
    ) -> None:
        """
        MultiValueRegister instance from name, values, clock, and last_update (all but the first are optional).
        :param name: SerializableType
        :param values: list[SerializableType]
        :param clock: ClockProtocol
        :param last_update: Any
        :param listeners: list[Callable[[UpdateProtocol], None]]
        :raises TypeError: name, values, clock, or listeners
        """
        if values is None:
            values = []
        if clock is None:
            clock = ScalarClock()
        if last_update is None:
            last_update = clock.default_time_stamp

        if listeners is None:
            listeners = []

        self.name = name
        self.values = values
        self.clock = clock
        self.last_update = last_update
        self.listeners = listeners

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes (encoded self
        """
        return pack([self.name, self.clock, self.last_update, self.values])

    @classmethod
    def unpack(cls, data: bytes, inject=None) -> MultiValueRegister:
        """
        Unpack the data bytes string into an instance.
        :param data: bytes
        :param inject: optional data to inject during unpacking
        :return: instance of self
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        name, clock, last_update, values = unpack(data, inject=inject)
        return cls(name, values, clock, last_update)

    def read(self, inject=None) -> tuple[SerializableType]:
        """
        Return the eventually consistent data view.
        :param inject: dict of optional data to inject during unpacking
        :return: tuple[SerializableType]
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        return tuple([unpack(pack(value), inject=inject) for value in self.values])

    @classmethod
    def compare_values(cls, left: SerializableType, right: SerializableType) -> bool:
        """
        True if left is greater than right, else False.
        :param left: SerializableType
        :param right: SerializableType
        :return: bool
        """
        return pack(left) > pack(right)

    def update(self, state_update: Update) -> MultiValueRegister:
        """
        Apply an update.
        :param state_update: Update
        :return: MultiValueRegister
        :raises ValueError: state_update invalid
        """
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")

        self.invoke_listeners(state_update)

        if self.clock.is_later(state_update.time_stamp, self.last_update):
            self.last_update = state_update.time_stamp
            self.values = [state_update.data]

        if self.clock.are_concurrent(state_update.time_stamp, self.last_update):
            if state_update.data not in self.values:
                self.values.append(state_update.data)
                self.values.sort(key=lambda item: pack(item))

        self.clock.update(state_update.time_stamp)

        return self

    def checksums(
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[int]:
        """
        Returns any checksums for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[int]
        """
        return (
            crc32(pack(self.last_update)),
            sum([crc32(pack(v)) for v in self.values]) % 2**32,
        )

    def history(
        self,
        /,
        *,
        from_time_stamp: Any = None,
        until_time_stamp: Any = None,
        update_class: Type[Update] = Update,
    ) -> tuple[Update]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for
        resynchronization by replaying updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :param update_class: type of update to use
        :return: tuple[Update]
        """
        if from_time_stamp is not None and self.clock.is_later(
            from_time_stamp, self.last_update
        ):
            return tuple()
        if until_time_stamp is not None and self.clock.is_later(
            self.last_update, until_time_stamp
        ):
            return tuple()

        return tuple(
            [
                update_class(
                    clock_uuid=self.clock.uuid, time_stamp=self.last_update, data=v
                )
                for v in self.values
            ]
        )

    def get_merkle_history(
        self, /, *, update_class: Type[Update] = Update
    ) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a history as merkle tree for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        :param update_class: type of update to use
        :return: list[bytes, list[bytes], dict[bytes, bytes]]
        """
        return get_merkle_tree(self, update_class=update_class)

    def resolve_merkle_histories(
        self, history: list[bytes, list[bytes]]
    ) -> list[bytes]:
        """
        Accept a history of form [root, leaves] from another node. Return the leaves that need to be resolved
        and merged for synchronization.
        :param history: list[bytes, list[bytes]]
        :return: list[bytes]
        """
        return resolve_merkle_tree(self, tree=history)

    def write(
        self, value: SerializableType, /, *, update_class: Type[Update] = Update
    ) -> Update:
        """
        Writes the new value to the register and returns an Update.
        :param value: SerializableType
        :param update_class: Type[Update]
        :return: Update
        :raises TypeError: value must be SerializableType
        """
        if not isinstance(value, SerializableType):
            raise TypeError(f"value must be SerializableType ({SerializableType})")

        state_update = update_class(
            clock_uuid=self.clock.uuid, time_stamp=self.clock.read(), data=value
        )
        self.update(state_update)

        return state_update

    def add_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Adds a listener that is called on each update.
        :param listener: Callable[[Update], None]
        :return: None
        """
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Removes a listener if it was previously added.
        :param listener: Callable[[Update], None]
        :return: None
        """
        self.listeners.remove(listener)

    def invoke_listeners(self, state_update: Update) -> None:
        """
        Invokes all event listeners, passing them the state_update.
        :param state_update: Update
        :return: None
        """
        for listener in self.listeners:
            listener(state_update)


class LastWriterWinsRegister:
    """Implements the Last Writer Wins Register CRDT."""

    name: SerializableType
    value: SerializableType
    clock: Clock
    last_update: Any
    last_writer: SerializableType
    listeners: list[Callable]

    def __init__(
        self,
        name: SerializableType,
        value: SerializableType = None,
        clock: Clock = None,
        last_update: Any = None,
        last_writer: SerializableType = None,
        listeners: list[Callable] = None,
    ) -> None:
        """
        LastWriterWinsRegister from a name, a value, and a shared clock.
        :param name: SerializableType
        :param value: SerializableType
        :param clock: ClockProtocol
        :param last_update: Any
        :param last_writer: SerializableType
        :param listeners: list[Callable[[UpdateProtocol], None
        :raises TypeError: name, value, clock, or last_writer
        """
        if clock is None:
            clock = ScalarClock()
        if last_update is None:
            last_update = clock.default_time_stamp
        if listeners is None:
            listeners = []

        self.name = name
        self.value = value
        self.clock = clock
        self.last_update = last_update
        self.last_writer = last_writer
        self.listeners = listeners

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes (encoded self)
        """
        return pack(
            [self.name, self.clock, self.value, self.last_update, self.last_writer]
        )

    @classmethod
    def unpack(cls, data: bytes, inject=None) -> LastWriterWinsRegister:
        """
        Unpack the data bytes string into an instance.
        :param data: bytes
        :param inject: optional data to inject during unpacking
        :return: instance of self
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        name, clock, value, last_update, last_writer = unpack(data, inject=inject)
        return cls(
            name=name,
            clock=clock,
            value=value,
            last_update=last_update,
            last_writer=last_writer,
        )

    def read(self, /, *, inject=None) -> SerializableType:
        """
        Return the eventually consistent data view.
        :param inject: dict
        :return: SerializableType
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        return unpack(pack(self.value), inject=inject)

    @classmethod
    def compare_values(cls, left: SerializableType, right: SerializableType) -> bool:
        """
        True if left is greater than right, else False.
        :param left: SerializableType
        :param right: SerializableType
        :return: bool
        """
        return pack(left) > pack(right)

    def update(self, state_update: Update, /, *, inject=None) -> LastWriterWinsRegister:
        """
        Apply an update.
        :param state_update: Update
        :param inject: dict
        :return: LastWriterWinsRegister
        :raises ValueError: state_update invalid
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")
        if len(state_update.data) != 2:
            raise ValueError(
                "state_update.data must be tuple of (int, SerializableType)"
            )

        self.invoke_listeners(state_update)

        if self.clock.is_later(state_update.time_stamp, self.last_update):
            self.last_update = state_update.time_stamp
            self.last_writer = state_update.data[0]
            self.value = state_update.data[1]
        elif self.clock.are_concurrent(state_update.time_stamp, self.last_update):
            if (state_update.data[0] > self.last_writer) or (
                state_update.data[0] == self.last_writer
                and self.compare_values(state_update.data[1], self.value)
            ):
                self.last_writer = state_update.data[0]
                self.value = state_update.data[1]

        self.clock.update(state_update.time_stamp)

        return self

    def checksums(
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[int, int, int]:
        """
        Returns any checksums for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[int]
        """
        return (
            crc32(pack(self.last_update)),
            crc32(pack(self.last_writer)),
            crc32(pack(self.value)),
        )

    def history(
        self,
        /,
        *,
        from_time_stamp: Any = None,
        until_time_stamp: Any = None,
        update_class: Type[Update] = Update,
    ) -> tuple[Update]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for resynchronization
        by replaying updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :param update_class: type of update to use
        :return: tuple[Update]
        """
        if from_time_stamp is not None and self.clock.is_later(
            from_time_stamp, self.last_update
        ):
            return tuple()
        if until_time_stamp is not None and self.clock.is_later(
            self.last_update, until_time_stamp
        ):
            return tuple()

        return (
            update_class(
                clock_uuid=self.clock.uuid,
                time_stamp=self.last_update,
                data=(self.last_writer, self.value),
            ),
        )

    def get_merkle_history(
        self, /, *, update_class: Type[Update] = Update
    ) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a history as merkle tree for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        """
        return get_merkle_tree(self, update_class=update_class)

    def resolve_merkle_histories(
        self, history: list[bytes, list[bytes]]
    ) -> list[bytes]:
        """
        Accept a history of form [root, leaves] from another node. Return the leaves that need to be resolved
        and merged for synchronization.
        :param history: list[bytes, list[bytes]]
        :return: list[bytes]
        """
        return resolve_merkle_tree(self, tree=history)

    def write(
        self,
        value: SerializableType,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Writes the new value to the register and returns an Update by default. Requires a SerializableType
        writer id for tie breaking.
        :param value: SerializableType
        :param writer: SerializableType
        :param update_class: Type[Update]
        :param inject: dict
        :return: Update
        :raises TypeError: value or writer must be SerializableType
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        if not (isinstance(value, SerializableType) or value is None):
            raise TypeError("value must be a SerializableType or None")
        if not isinstance(writer, SerializableType):
            raise TypeError(f"writer must be an SerializableType ({SerializableType})")

        state_update = update_class(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=(writer, value),
        )
        self.update(state_update, inject=inject)

        return state_update

    def add_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Adds a listener that is called on each update.
        :param listener: Callable[[Update], None]
        :return: None
        """
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Removes a listener if it was previously added.
        :param listener: Callable[[Update], None]
        :return: None
        """
        self.listeners.remove(listener)

    def invoke_listeners(self, state_update: Update) -> None:
        """
        Invokes all event listeners, passing them the state_update.
        :param state_update: Update
        :return: None
        """
        for listener in self.listeners:
            listener(state_update)
