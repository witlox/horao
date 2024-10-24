from __future__ import annotations

import logging
from binascii import crc32
from dataclasses import dataclass, field
from typing import (
    Callable,
    Any,
    Hashable,
    Optional,
    TypeVar,
    Generic,
    List,
    Iterable,
)

from packify import SerializableType, pack, unpack

from horao.models.decorators import instrument_class_function
from horao.models.internal import (
    ScalarClock,
    Update,
    get_merkle_tree,
    resolve_merkle_tree,
    CRDT,
)


class LastWriterWinsMap(CRDT):
    """Last Writer Wins Map CRDT."""

    names: ObservedRemovedSet
    registers: dict[SerializableType, LastWriterWinsRegister]
    listeners: list[Callable]

    def __init__(
        self,
        names: ObservedRemovedSet = None,
        registers: dict = None,
        listeners: list[Callable] = None,
    ) -> None:
        """
        Initialize an LastWriterWinsMap from an ObservedRemovedSet of names, a dict mapping
        names to LastWriterWinsRegisters, and a shared clock.
        :param names: ObservedRemovedSet
        :param registers: dict
        :param listeners: list[Callable]
        :raises TypeError: registers not filled with correct values (and/or types)
        """
        if listeners is None:
            listeners = []

        names = ObservedRemovedSet() if names is None else names
        registers = {} if registers is None else registers
        clock = ScalarClock()

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

        if o == "o":
            self.names.update(
                Update(self.clock.uuid, time_stamp, ("o", n)), inject=inject
            )
            if n not in self.registers and n in self.names.read():
                self.registers[n] = LastWriterWinsRegister(
                    n, w, self.clock, time_stamp, w
                )

        if o == "r":
            self.names.update(
                Update(self.clock.uuid, time_stamp, ("r", n)), inject=inject
            )

            if n not in self.names.read(inject=inject) and n in self.registers:
                del self.registers[n]

        if n in self.registers:
            self.registers[n].update(
                Update(self.clock.uuid, time_stamp, (w, w)), inject=inject
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
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[Update, ...]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for
        resynchronization by replaying updates from divergent nodes.
        :param from_time_stamp: Any
        :param until_time_stamp: Any
        :return: tuple[Update]
        """
        registers_history: dict[SerializableType, tuple[Update]] = {}
        orset_history = self.names.history(
            from_time_stamp=from_time_stamp, until_time_stamp=until_time_stamp
        )
        history = []

        for name in self.registers:
            registers_history[name] = self.registers[name].history(
                from_time_stamp=from_time_stamp, until_time_stamp=until_time_stamp
            )

        for update in orset_history:
            name = update.data[1]
            if name in registers_history:
                register_update = registers_history[name][0]
                history.append(
                    Update(
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
                    Update(
                        clock_uuid=update.clock_uuid,
                        time_stamp=update.time_stamp,
                        data=(update.data[0], name, 0, None),
                    )
                )

        return tuple(history)

    def get_merkle_history(self) -> list[bytes | list[bytes] | dict[bytes, bytes]]:
        """
        Get a history as merkle tree for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        :return: list[bytes, list[bytes], dict[bytes, bytes]]
        """
        return get_merkle_tree(self)

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
        self, name: Hashable, value: SerializableType, writer: SerializableType
    ) -> Update:
        """
        Extends the dict with name: value. Returns an Update that should be propagated to all nodes.
        :param name: Hashable
        :param value: SerializableType
        :param writer: SerializableType
        :return: Update
        """
        state_update = Update(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=("o", name, writer, value),
        )
        self.update(state_update)

        return state_update

    def unset(self, name: Hashable, writer: SerializableType) -> Update:
        """
        Removes the key name from the dict.
        :param name: Hashable
        :param writer: SerializableType
        :return: Update
        """
        state_update = Update(
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


@dataclass
class ObservedRemovedSet(CRDT):
    """
    Observed Removed Set (ORSet) CRDT. Comprised of two Sets with a read method that removes the removed set members
    from the observed set. Add-biased.
    """

    observed: set[SerializableType] = field(default_factory=set)
    observed_metadata: dict[SerializableType, Update] = field(default_factory=dict)
    removed: set[SerializableType] = field(default_factory=set)
    removed_metadata: dict[SerializableType, Update] = field(default_factory=dict)
    clock: ScalarClock = field(default_factory=ScalarClock)
    cache: Optional[tuple] = field(default=None)
    listeners: list[Callable] = field(default_factory=list)

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes
        """
        return pack(
            [
                self.observed,
                self.observed_metadata,
                self.removed,
                self.removed_metadata,
                self.clock,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, inject=None) -> ObservedRemovedSet:
        """
        Unpack the data bytes string into an instance.
        :param data: bytes
        :param inject: optional data to inject during unpacking
        :return: ObservedRemovedSet
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        observed, observed_metadata, removed, removed_metadata, clock = unpack(
            data, inject=inject
        )
        return cls(observed, observed_metadata, removed, removed_metadata, clock)

    def read(self, /, *, inject=None) -> set[SerializableType]:
        """
        Return the eventually consistent data view.
        :param inject: dict of optional data to inject during unpacking
        :return: set[SerializableType]
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        if self.cache is not None:
            if self.cache[0] == self.clock.read():
                return self.cache[1]

        difference = self.observed.difference(self.removed)
        self.cache = (self.clock.read(), difference)

        return difference

    def update(self, state_update: Update, /, *, inject=None) -> ObservedRemovedSet:
        """
        Apply an update.
        :param state_update: Update
        :param inject: dict of optional data to inject during unpacking
        :return: ObservedRemovedSet
        :raises ValueError: state_update invalid
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")
        if len(state_update.data) != 2:
            raise ValueError("state_update.data must be 2 long")
        if state_update.data[0] not in ("o", "r"):
            raise ValueError("state_update.data[0] must be in ('o', 'r')")

        self.invoke_listeners(state_update)
        o, m = state_update.data
        time_stamp = state_update.time_stamp

        if o == "o":
            if m not in self.removed or (
                m in self.removed_metadata
                and not self.clock.is_later(self.removed_metadata[m], time_stamp)
            ):
                self.observed.add(m)
                if m in self.observed_metadata:
                    oldts = self.observed_metadata[m]
                else:
                    oldts = self.clock.default_time_stamp
                if self.clock.is_later(time_stamp, oldts):
                    self.observed_metadata[m] = time_stamp

                if m in self.removed:
                    self.removed.remove(m)
                    del self.removed_metadata[m]

                self.cache = None

        if o == "r":
            if m not in self.observed or (
                m in self.observed_metadata
                and self.clock.is_later(time_stamp, self.observed_metadata[m])
            ):
                self.removed.add(m)
                if m in self.removed_metadata:
                    oldts = self.removed_metadata[m]
                else:
                    oldts = self.clock.default_time_stamp
                if self.clock.is_later(time_stamp, oldts):
                    self.removed_metadata[m] = time_stamp

                if m in self.observed:
                    self.observed.remove(m)
                    del self.observed_metadata[m]

                self.cache = None

        self.clock.update(time_stamp)

        return self

    def checksums(
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[int | Any, int | Any, int | Any, int | Any]:
        """
        Returns any checksums for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[int]
        """
        observed, removed = 0, 0
        total_observed_crc32 = 0
        total_removed_crc32 = 0
        for member, ts in self.observed_metadata.items():
            if from_time_stamp is not None:
                if self.clock.is_later(from_time_stamp, ts):
                    continue
            if until_time_stamp is not None:
                if self.clock.is_later(ts, until_time_stamp):
                    continue

            observed += 1
            total_observed_crc32 += crc32(pack(member))

        for member, ts in self.removed_metadata.items():
            if from_time_stamp is not None:
                if self.clock.is_later(from_time_stamp, ts):
                    continue
            if until_time_stamp is not None:
                if self.clock.is_later(ts, until_time_stamp):
                    continue

            removed += 1
            total_removed_crc32 += crc32(pack(member))

        return (
            observed,
            removed,
            total_observed_crc32 % 2**32,
            total_removed_crc32 % 2**32,
        )

    def history(
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[Update, ...]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for
        resynchronization by replaying updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[Update]
        """
        updates = []

        for o in self.observed:
            if from_time_stamp is not None and self.clock.is_later(
                from_time_stamp, self.observed_metadata[o]
            ):
                continue
            if until_time_stamp is not None and self.clock.is_later(
                self.observed_metadata[o], until_time_stamp
            ):
                continue
            updates.append(
                Update(
                    clock_uuid=self.clock.uuid,
                    time_stamp=self.observed_metadata[o],
                    data=("o", o),
                )
            )

        for r in self.removed:
            if from_time_stamp is not None and self.clock.is_later(
                from_time_stamp, self.removed_metadata[r]
            ):
                continue
            if until_time_stamp is not None and self.clock.is_later(
                self.removed_metadata[r], until_time_stamp
            ):
                continue
            updates.append(
                Update(
                    clock_uuid=self.clock.uuid,
                    time_stamp=self.removed_metadata[r],
                    data=("r", r),
                )
            )

        return tuple(updates)

    def get_merkle_history(self) -> list[bytes | list[bytes] | dict[bytes, bytes]]:
        """
        Get a history as merkle tree for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        :return: list[bytes, list[bytes], dict[bytes, bytes]]
        """
        return get_merkle_tree(self)

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

    def observe(self, member: SerializableType) -> Update:
        """
        Creates, applies, and returns an Update that adds the given member to the observed set. The
        member will be in the data attribute at index 1.
        :param member: SerializableType
        :return: Update
        :raises TypeError: member is not SerializableType
        """
        state_update = Update(
            clock_uuid=self.clock.uuid, time_stamp=self.clock.read(), data=("o", member)
        )

        self.update(state_update)

        return state_update

    def remove(self, member: SerializableType) -> Update:
        """
        Creates, applies, and returns an Update that adds the given member to the removed set.
        :param member: SerializableType
        :return: Update
        """
        state_update = Update(
            clock_uuid=self.clock.uuid, time_stamp=self.clock.read(), data=("r", member)
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


class MultiValueRegister(CRDT):
    """Implements the Multi-Value Register CRDT."""

    name: SerializableType
    values: list[SerializableType]
    clock: ScalarClock
    last_update: Any
    listeners: list[Callable]

    def __init__(
        self,
        name: SerializableType,
        values=None,
        clock: ScalarClock = None,
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

    def read(self, inject=None) -> tuple[Any, ...]:
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
    ) -> tuple[int, int | Any]:
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
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[Any] | tuple[Update, ...]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for
        resynchronization by replaying updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
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
                Update(clock_uuid=self.clock.uuid, time_stamp=self.last_update, data=v)
                for v in self.values
            ]
        )

    def get_merkle_history(self) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a history as merkle tree for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        :return: list[bytes, list[bytes], dict[bytes, bytes]]
        """
        return get_merkle_tree(self)

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

    def write(self, value: SerializableType) -> Update:
        """
        Writes the new value to the register and returns an Update.
        :param value: SerializableType
        :return: Update
        :raises TypeError: value must be SerializableType
        """
        state_update = Update(
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


class LastWriterWinsRegister(CRDT):
    """Implements the Last Writer Wins Register CRDT."""

    name: SerializableType
    value: SerializableType
    clock: ScalarClock
    last_update: Any
    last_writer: SerializableType
    listeners: list[Callable]

    def __init__(
        self,
        name: SerializableType,
        value: SerializableType = None,
        clock: ScalarClock = None,
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
        :param inject: optional dict
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
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[Update]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for resynchronization
        by replaying updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
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
            Update(
                clock_uuid=self.clock.uuid,
                time_stamp=self.last_update,
                data=(self.last_writer, self.value),
            ),
        )

    def get_merkle_history(self) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a history as merkle tree for the Updates of the form [root, [content_id for update in self.history()], {
        content_id: packed for update in self.history()}] where packed is the result of update.pack() and content_id
        is the sha256 of the packed update.
        """
        return get_merkle_tree(self)

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
        inject=None,
    ) -> Update:
        """
        Writes the new value to the register and returns an Update by default. Requires a SerializableType
        writer id for tie breaking.
        :param value: SerializableType
        :param writer: SerializableType
        :param inject: dict
        :return: Update
        :raises TypeError: value or writer must be SerializableType
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}

        state_update = Update(
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


T = TypeVar("T", bound=CRDT)


class CRDTList(Generic[T]):
    """CRDTList behaves as a list of instances T that can be updated concurrently."""

    def __init__(
        self,
        content: List[T] = None,
        items: LastWriterWinsMap = None,
        inject=None,
    ) -> None:
        """
        Initialize from an LastWriterWinsMap of item positions and a shared clock if supplied otherwise default.
        :param content: list of T instances
        :param items: LastWriterWinsMap of T items
        :param inject: optional data to inject during unpacking
        """
        self.inject = {**globals()} if not inject else {**globals(), **inject}
        self.log = logging.getLogger(__name__)
        self.hardware = LastWriterWinsMap() if not items else items
        if content:
            self.extend(content)
        self.iterator = 0

    @instrument_class_function(name="append", level=logging.DEBUG)
    def append(self, item: T) -> T:
        """
        Append a hardware instance to the list
        :param item: instance of Hardware
        :return: inserted item
        """
        self.hardware.set(len(self), item, hash(item))
        return item

    def clear(self) -> None:
        """
        Clear the list, not the history
        :return: None
        """
        # todo check history is consistent
        self.iterator = 0
        self.hardware = LastWriterWinsMap()

    def copy(self) -> CRDTList[T]:
        results = CRDTList(inject=self.inject)
        results.extend(iter(self))
        return results

    def count(self):
        return len(self)

    def extend(self, other: Iterable[T]) -> CRDTList[T]:
        for item in other:
            self.hardware.set(len(self), item, hash(item))
        return self

    def index(self, item: T) -> int:
        """
        Return the index of the hardware instance
        :param item: instance to search for
        :return: int
        :raises ValueError: item not found
        """
        result = next(
            iter([i for i, h in self.hardware.read(inject=self.inject) if h == item]),
            None,
        )
        if result is None:
            self.log.error(f"{item.name} not found.")
            raise ValueError(f"{item} not found.")
        return result

    def insert(self, index: int, item: T) -> None:
        self.hardware.set(index, item, hash(item))

    @instrument_class_function(name="pop", level=logging.DEBUG)
    def pop(self, index: int, default: T = None) -> Optional[T]:
        if index >= len(self):
            self.log.debug(f"Index {index} out of bounds, returning default.")
            return default
        item = self.hardware.read(inject=self.inject)[index]
        self.hardware.unset(item, hash(item))
        return item

    @instrument_class_function(name="remove", level=logging.DEBUG)
    def remove(self, item: T) -> None:
        """
        Remove a hardware instance from the list
        :param item: instance of Hardware
        :return: None
        :raises ValueError: item not found
        """
        local_item = next(
            iter([h for _, h in self.hardware.read(inject=self.inject) if h == item]),
            None,
        )
        if not local_item:
            self.log.debug(f"{item.name} not found.")
            raise ValueError(f"{item} not found.")
        self.hardware.unset(local_item, hash(item))

    def reverse(self) -> None:
        """
        cannot reverse a list inplace in a CRDT
        :return: None
        :raises: NotImplementedError
        """
        raise NotImplementedError("Cannot reverse a list inplace in a CRDT")

    def sort(self, item: T = None, reverse: bool = False) -> None:
        """
        cannot sort a list inplace in a CRDT
        :return: None
        :raises: NotImplementedError
        """
        raise NotImplementedError("Cannot sort a list inplace in a CRDT")

    def __len__(self) -> int:
        return len(self.hardware.read(inject=self.inject))

    def __eq__(self, other: CRDTList[T]) -> bool:
        return self.hardware.read(inject=self.inject) == other.hardware.read(
            inject=self.inject
        )

    def __ne__(self, other: CRDTList[T]) -> bool:
        return self.hardware.read(inject=self.inject) != other.hardware.read(
            inject=self.inject
        )

    def __contains__(self, item: T) -> bool:
        return item in self.hardware.read(inject=self.inject)

    def __delitem__(self, item: T) -> None:
        if item not in self.hardware.read(inject=self.inject):
            raise KeyError(f"{item} not found.")
        self.remove(item)

    def __getitem__(self, index: int) -> T:
        return self.hardware.read(inject=self.inject)[index]

    def __setitem__(self, index: int, value: T) -> None:
        self.hardware.set(index, value, hash(value))

    def __iter__(self) -> Iterable[T]:
        for _, item in self.hardware.read(inject=self.inject):
            yield item

    def __next__(self) -> T:
        if self.iterator >= len(self):
            self.iterator = 0
            raise StopIteration
        item = self.hardware.read(inject=self.inject)[self.iterator]
        self.iterator += 1
        return item

    def __add__(self, other: CRDTList[T]) -> CRDTList[T]:
        return self.extend(iter(other))

    def __sub__(self, other: CRDTList[T]) -> CRDTList[T]:
        for item in iter(other):
            self.remove(item)
        return self

    def __repr__(self) -> str:
        return f"HardwareList({self.hardware.read(inject=self.inject)})"

    def __reversed__(self) -> CRDTList[T]:
        return self.hardware.read(inject=self.inject)[::-1]

    def __sizeof__(self) -> int:
        return self.count()

    def __hash__(self):
        return hash(self.hardware)

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes
        """
        return self.hardware.pack()

    @classmethod
    def unpack(cls, data: bytes, /, *, inject=None) -> CRDTList[T]:
        """
        Unpack the data bytes string into an instance.
        :param data: serialized FractionallyIndexedArray needing unpacking
        :param inject: optional data to inject during unpacking
        :return: FractionallyIndexedArray
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        positions = LastWriterWinsMap.unpack(data, inject)
        return cls(items=positions, inject=inject)
