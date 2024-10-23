from __future__ import annotations

from binascii import crc32
from typing import Any, Callable, Hashable, Type

from packify import SerializableType, pack, unpack

from .clock import ScalarClock
from .data_types import Nothing
from .helpers import get_merkle_tree, resolve_merkle_tree
from .protocols import Clock
from .register import LastWriterWinsRegister, MultiValueRegister
from .set import ObservedRemovedSet
from .update import Update


class MultiValueMap:
    """Map CRDT using Multi-Value Registers"""

    names: ObservedRemovedSet
    registers: dict[SerializableType, MultiValueRegister]
    clock: Clock
    listeners: list[Callable]

    def __init__(
        self,
        names: ObservedRemovedSet = None,
        registers: dict = None,
        clock: Clock = None,
        listeners: list[Callable] = None,
    ) -> None:
        """
        MultiValueMap from an ObservedRemovedSet of names, a dict mapping names to MultiValueRegisters,
        and a shared clock.
        :param names: ObservedRemovedSet
        :param registers: dict
        :param clock: Clock
        :param listeners: list[Callable]
        :raises TypeError: registers not filled with correct values (and/or types)
        """
        if listeners is None:
            listeners = []

        names = ObservedRemovedSet() if names is None else names
        registers = {} if registers is None else registers
        clock = ScalarClock() if clock is None else clock

        names.clock = clock

        for name in registers:
            registers[name].clock = clock

        self.names = names
        self.registers = registers
        self.clock = clock
        self.listeners = listeners

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes
        """
        return pack([self.clock, self.names, self.registers])

    @classmethod
    def unpack(cls, data: bytes, inject=None) -> MultiValueMap:
        """
        Unpack the data bytes string into an instance.
        :param inject:
        :param data: bytes
        :return: MultiValueMap
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        clock, names, registers = unpack(data, inject=inject)
        return cls(names, registers, clock)

    def read(self, inject=None) -> dict:
        """
        Return the eventually consistent data view.
        :param inject: optional dict
        :return: dict
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}

        result = {}

        for name in self.names.read():
            result[name] = self.registers[name].read(inject=inject)

        return result

    def update(self, state_update: Update) -> MultiValueMap:
        """
        Apply an update.
        :param state_update: Update
        :return: self (MultiValueMap)
        :raises ValueError: invalid state_update
        """
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")
        if len(state_update.data) != 3:
            raise ValueError(
                f"state_update.data must be tuple of (str, SerializableType ({SerializableType}), SerializableType ({SerializableType}))"
            )

        o, n, v = state_update.data
        if o not in ("o", "r"):
            raise ValueError("state_update.data[0] must be str op one of ('o', 'r')")

        self.invoke_listeners(state_update)
        time_stamp = state_update.time_stamp

        if o == "o":
            self.names.update(Update(self.clock.uuid, time_stamp, ("o", n)))
            if n not in self.registers and n in self.names.read():
                self.registers[n] = MultiValueRegister(n, [v], self.clock, time_stamp)

        if o == "r":
            self.names.update(Update(self.clock.uuid, time_stamp, ("r", n)))
            if n not in self.names.read() and n in self.registers:
                del self.registers[n]

        if n in self.registers:
            self.registers[n].update(Update(self.clock.uuid, time_stamp, v))

        return self

    def checksums(
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[int | Any, int | Any, Any]:
        """
        Returns any checksums for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: Any
        :param until_time_stamp: Any
        :return: tuple[int]
        """
        names_checksums = self.names.checksums(
            from_time_stamp=from_time_stamp, until_time_stamp=until_time_stamp
        )
        total_last_update = 0
        total_register_crc32 = 0

        for name in self.registers:
            ts = self.registers[name].last_update
            if from_time_stamp is not None:
                if self.clock.is_later(from_time_stamp, ts):
                    continue
            if until_time_stamp is not None:
                if self.clock.is_later(ts, until_time_stamp):
                    continue

            packed = pack(self.registers[name].name)
            packed += pack([v for v in self.registers[name].values])
            total_register_crc32 += crc32(packed)
            total_last_update += crc32(pack(self.registers[name].last_update))

        return (
            total_last_update % 2**32,
            total_register_crc32 % 2**32,
            *names_checksums,
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
        :param from_time_stamp: Any
        :param until_time_stamp: Any
        :param update_class: Type[Update]
        :return: tuple[Update]
        """
        registers_history: dict[SerializableType, tuple[Update]] = {}
        observed_removed_set_history = self.names.history(
            from_time_stamp=from_time_stamp,
            until_time_stamp=until_time_stamp,
            update_class=update_class,
        )
        history = []

        for name in self.registers:
            registers_history[name] = self.registers[name].history(
                from_time_stamp=from_time_stamp,
                until_time_stamp=until_time_stamp,
                update_class=update_class,
            )

        for update in observed_removed_set_history:
            name = update.data[1]
            if name in registers_history:
                register_update = registers_history[name][0]
                update_class = register_update.__class__
                history.append(
                    update_class(
                        clock_uuid=update.clock_uuid,
                        time_stamp=register_update.time_stamp,
                        data=(update.data[0], name, register_update.data),
                    )
                )
            else:
                history.append(
                    update_class(
                        clock_uuid=update.clock_uuid,
                        time_stamp=update.time_stamp,
                        data=(update.data[0], name, Nothing()),
                    )
                )

        return tuple(history)

    def get_merkle_history(
        self, /, *, update_class: Type[Update] = Update
    ) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a history as merkle tree for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        :param update_class: Type[Update]
        :return: list[bytes, list[bytes], dict[bytes, bytes
        """
        return get_merkle_tree(self, update_class=update_class)

    def resolve_merkle_histories(
        self, history: list[bytes, list[bytes]]
    ) -> list[bytes]:
        """
        Accept a history of form [root, leaves] from another node. Return the leaves that need to be
        resolved and merged for synchronization.
        :param history: list[bytes, list[bytes]]
        :return: list[bytes]
        """
        return resolve_merkle_tree(self, tree=history)

    def set(
        self,
        name: SerializableType,
        value: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
    ) -> Update:
        """
        Extends the dict with name: value. Returns an Update that should be propagated to all nodes.
        :param name: SerializableType
        :param value: SerializableType
        :param update_class: Type[Update]
        :return: Update
        """
        state_update = update_class(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=("o", name, value),
        )
        self.update(state_update)

        return state_update

    def unset(
        self, name: SerializableType, /, *, update_class: Type[Update] = Update
    ) -> Update:
        """
        Removes the key name from the dict.
        :param name: SerializableType
        :param update_class: Type[Update]
        :return: Update
        """
        state_update = update_class(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=("r", name, Nothing()),
        )
        self.update(state_update)

        return state_update

    def add_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Adds a listener that is called on each update.
        :param listener: to add
        :return: None
        """
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Removes a listener if it was previously added.
        :param listener: to remove
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


class LastWriterWinsMap:
    """Last Writer Wins Map CRDT."""

    names: ObservedRemovedSet
    registers: dict[SerializableType, LastWriterWinsRegister]
    clock: Clock
    listeners: list[Callable]

    def __init__(
        self,
        names: ObservedRemovedSet = None,
        registers: dict = None,
        clock: Clock = None,
        listeners: list[Callable] = None,
    ) -> None:
        """
        Initialize an LastWriterWinsMap from an ObservedRemovedSet of names, a dict mapping
        names to LastWriterWinsRegisters, and a shared clock.
        :param names: ObservedRemovedSet
        :param registers: dict
        :param clock: Clock
        :param listeners: list[Callable]
        :raises TypeError: registers not filled with correct values (and/or types)
        """
        if listeners is None:
            listeners = []

        names = ObservedRemovedSet() if names is None else names
        registers = {} if registers is None else registers
        clock = ScalarClock() if clock is None else clock

        names.clock = clock

        for name in registers:
            registers[name].clock = clock

        self.names = names
        self.registers = registers
        self.clock = clock
        self.listeners = listeners

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes
        """
        return pack(
            [
                self.clock,
                self.names,
                self.registers,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, inject=None) -> LastWriterWinsMap:
        """
        Unpack the data bytes string into an instance.
        :param data: bytes
        :param inject: optional dict
        :return: LastWriterWinsMap
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        clock, names, registers = unpack(data, inject=inject)
        return cls(names, registers, clock)

    def read(self, inject=None) -> dict:
        """
        Return the eventually consistent data view.
        :param inject: optional dict
        :return: dict
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}

        result = {}
        for name in self.names.read(inject=inject):
            result[name] = self.registers[name].read(inject=inject)

        return result

    def update(self, state_update: Update, /, *, inject=None) -> LastWriterWinsMap:
        """
        Apply an update.
        :param state_update: Update
        :param inject: dict
        :return: self (LastWriterWinsMap)
        :raises TypeError: invalid state_update data
        :raises ValueError: invalid state_update
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")
        if len(state_update.data) != 4:
            raise ValueError(
                "state_update.data must be tuple of (str, Hashable, int, SerializableType)"
            )

        o, n, w, w = state_update.data
        if not (type(o) is str and o in ("o", "r")):
            raise TypeError("state_update.data[0] must be str op one of ('o', 'r')")

        self.invoke_listeners(state_update)
        time_stamp = state_update.time_stamp
        update_class = state_update.__class__

        if o == "o":
            self.names.update(
                update_class(self.clock.uuid, time_stamp, ("o", n)), inject=inject
            )
            if n not in self.registers and n in self.names.read():
                self.registers[n] = LastWriterWinsRegister(
                    n, w, self.clock, time_stamp, w
                )

        if o == "r":
            self.names.update(
                update_class(self.clock.uuid, time_stamp, ("r", n)), inject=inject
            )

            if n not in self.names.read(inject=inject) and n in self.registers:
                del self.registers[n]

        if n in self.registers:
            self.registers[n].update(
                update_class(self.clock.uuid, time_stamp, (w, w)), inject=inject
            )

        return self

    def checksums(
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[int | Any, int | Any, int | Any, Any]:
        """
        Returns any checksums for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: Any
        :param until_time_stamp: Any
        :return: tuple[int]
        """
        names_checksums = self.names.checksums(
            from_time_stamp=from_time_stamp, until_time_stamp=until_time_stamp
        )
        total_last_update = 0
        total_last_writer = 0
        total_register_crc32 = 0

        for name in self.registers:
            ts = self.registers[name].last_update
            if from_time_stamp is not None:
                if self.clock.is_later(from_time_stamp, ts):
                    continue
            if until_time_stamp is not None:
                if self.clock.is_later(ts, until_time_stamp):
                    continue
            total_register_crc32 += crc32(
                pack(self.registers[name].name) + pack(self.registers[name].value)
            )
            total_last_update += crc32(pack(self.registers[name].last_update))
            total_last_writer += crc32(pack(self.registers[name].last_writer))

        return (
            total_last_update % 2**32,
            total_last_writer % 2**32,
            total_register_crc32 % 2**32,
            *names_checksums,
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
        :param from_time_stamp: Any
        :param until_time_stamp: Any
        :param update_class: Type[Update]
        :return: tuple[Update]
        """
        registers_history: dict[SerializableType, tuple[Update]] = {}
        orset_history = self.names.history(
            from_time_stamp=from_time_stamp,
            until_time_stamp=until_time_stamp,
            update_class=update_class,
        )
        history = []

        for name in self.registers:
            registers_history[name] = self.registers[name].history(
                from_time_stamp=from_time_stamp,
                until_time_stamp=until_time_stamp,
                update_class=update_class,
            )

        for update in orset_history:
            name = update.data[1]
            if name in registers_history:
                register_update = registers_history[name][0]
                update_class = register_update.__class__
                history.append(
                    update_class(
                        clock_uuid=update.clock_uuid,
                        time_stamp=register_update.time_stamp,
                        data=(
                            update.data[0],
                            name,
                            register_update.data[0],
                            register_update.data[1],
                        ),
                    )
                )
            else:
                history.append(
                    update_class(
                        clock_uuid=update.clock_uuid,
                        time_stamp=update.time_stamp,
                        data=(update.data[0], name, 0, None),
                    )
                )

        return tuple(history)

    def get_merkle_history(
        self, /, *, update_class: Type[Update] = Update
    ) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a history as merkle tree for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        :param update_class: Type[Update]
        :return: list[bytes, list[bytes], dict[bytes, bytes]]
        """
        return get_merkle_tree(self, update_class=update_class)

    def resolve_merkle_histories(
        self, history: list[bytes, list[bytes]]
    ) -> list[bytes]:
        """
        Accept a history of form [root, leaves] from another node.  Return the leaves that
        need to be resolved and merged for synchronization.
        :param history: list[bytes, list[bytes]]
        :return: list[bytes]
        """
        return resolve_merkle_tree(self, tree=history)

    def set(
        self,
        name: Hashable,
        value: SerializableType,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
    ) -> Update:
        """
        Extends the dict with name: value. Returns an Update that should be propagated to all nodes.
        :param name: Hashable
        :param value: SerializableType
        :param writer: SerializableType
        :param update_class: Type[Update]
        :return: Update
        """
        state_update = update_class(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=("o", name, writer, value),
        )
        self.update(state_update)

        return state_update

    def unset(
        self,
        name: Hashable,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
    ) -> Update:
        """
        Removes the key name from the dict.
        :param name: Hashable
        :param writer: SerializableType
        :param update_class: Type[Update]
        :return: Update
        """
        state_update = update_class(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=("r", name, writer, None),
        )
        self.update(state_update)

        return state_update

    def add_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Adds a listener that is called on each update.
        :param listener: to add
        :return: None
        """
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Removes a listener if it was previously added.
        :param listener: to remove
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
