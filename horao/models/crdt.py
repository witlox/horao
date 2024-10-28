# -*- coding: utf-8 -*-#
"""Conflict-free Replicated Data Types (CRDTs) for eventual consistency."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Hashable,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

from horao.models.decorators import instrument_class_function
from horao.models.internal import CRDT, LogicalClock, Update, UpdateType


@dataclass
class ObservedRemovedSet(CRDT):
    """
    Observed Removed Set (ORSet) CRDT. Comprised of two Sets with a read method that removes the removed set members
    from the observed set. Add-biased.
    """

    observed: Set[Hashable] = field(default_factory=set)
    observed_metadata: Dict[Hashable, Update] = field(default_factory=dict)
    removed: Set[Hashable] = field(default_factory=set)
    removed_metadata: Dict[Hashable, Update] = field(default_factory=dict)
    clock: LogicalClock = field(default_factory=LogicalClock)
    cache: Optional[Tuple] = field(default=None)
    listeners: List[Callable] = field(default_factory=list)

    def read(self) -> set[Hashable]:
        """
        Return the eventually consistent data view.
        :return: set of values
        """
        if self.cache is not None:
            if self.cache[0] == self.clock.read():
                return self.cache[1]

        difference = self.observed.difference(self.removed)
        self.cache = (self.clock.read(), difference)

        return difference

    def update(self, state_update: Update) -> ObservedRemovedSet:
        """
        Apply an update.
        :param state_update: Update
        :return: ObservedRemovedSet
        :raises ValueError: state_update invalid
        """
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")

        self.invoke_listeners(state_update)

        if state_update.update_type == UpdateType.Observed:
            if state_update.data not in self.removed or (
                state_update.data in self.removed_metadata
                and not self.clock.is_later(
                    self.removed_metadata[state_update.data].time_stamp,
                    state_update.time_stamp,
                )
            ):
                self.observed.add(state_update.data)
                self.observed_metadata[state_update.data] = state_update

                if state_update.data in self.removed:
                    self.removed.remove(state_update.data)

                self.cache = None

        if state_update.update_type == UpdateType.Removed:
            if state_update.data not in self.removed or (
                state_update.data in self.removed_metadata
                and self.clock.is_later(
                    state_update.time_stamp,
                    self.observed_metadata[state_update.data].time_stamp,
                )
            ):
                self.removed.add(state_update.data)
                self.removed_metadata[state_update.data] = state_update

                if state_update.data in self.observed:
                    self.observed.remove(state_update.data)

                self.cache = None

        self.clock.update()

        return self

    def checksum(
        self, /, *, from_time_stamp: float = None, until_time_stamp: float = None
    ) -> Tuple[int, ...]:
        """
        Returns any checksums for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[int, int]
        """

        def retrieve(s: Dict[Hashable, Update]) -> list[Hashable]:
            result = []
            for m, u in s.items():
                if from_time_stamp is not None:
                    if self.clock.is_later(from_time_stamp, u.time_stamp):
                        continue
                if until_time_stamp is not None:
                    if self.clock.is_later(u.time_stamp, until_time_stamp):
                        continue
                result.append(m)
            return result

        observed = retrieve(self.observed_metadata)
        removed = retrieve(self.removed_metadata)

        return hash(frozenset(observed)), hash(frozenset(removed))

    def history(
        self, /, *, from_time_stamp: float = None, until_time_stamp: float = None
    ) -> tuple[Update, ...]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for
        resynchronization by replaying updates from divergent nodes.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[Update]
        """
        updates = []

        for observed in self.observed:
            if from_time_stamp is not None and self.clock.is_later(
                from_time_stamp, self.observed_metadata[observed].time_stamp
            ):
                continue
            if until_time_stamp is not None and self.clock.is_later(
                self.observed_metadata[observed].time_stamp, until_time_stamp
            ):
                continue
            updates.append(
                Update(
                    clock_uuid=self.clock.uuid,
                    time_stamp=self.observed_metadata[observed].time_stamp,
                    data=observed,
                    update_type=UpdateType.Observed,
                    writer=None,
                    name=None,
                )
            )

        for removed in self.removed:
            if from_time_stamp is not None and self.clock.is_later(
                from_time_stamp, self.removed_metadata[removed].time_stamp
            ):
                continue
            if until_time_stamp is not None and self.clock.is_later(
                self.removed_metadata[removed].time_stamp, until_time_stamp
            ):
                continue
            updates.append(
                Update(
                    clock_uuid=self.clock.uuid,
                    time_stamp=self.removed_metadata[removed].time_stamp,
                    data=removed,
                    update_type=UpdateType.Removed,
                    writer=None,
                    name=None,
                )
            )

        return tuple(updates)

    def observe(self, member: Hashable) -> Update:
        """
        Creates, applies, and returns an Update that adds the given member to the observed set. The
        member will be in the data attribute at index 1.
        :param member: thing to add
        :return: Update
        :raises TypeError: member is not SerializableType
        """
        state_update = Update(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=member,
            update_type=UpdateType.Observed,
            writer=None,
            name=None,
        )

        self.update(state_update)

        return state_update

    def remove(self, member: Hashable) -> Update:
        """
        Creates, applies, and returns an Update that adds the given member to the removed set.
        :param member: thing to remove
        :return: Update
        """
        state_update = Update(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=member,
            update_type=UpdateType.Removed,
            writer=None,
            name=None,
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

    name: Hashable
    value: Hashable
    clock: LogicalClock
    last_update: Any
    last_writer: Hashable
    listeners: list[Callable]

    def __init__(
        self,
        name: Hashable,
        value: Hashable = None,
        clock: LogicalClock = None,
        last_update: float = None,
        last_writer: Hashable = None,
        listeners: list[Callable] = None,
    ) -> None:
        """
        LastWriterWinsRegister from a name, a value, and a shared clock.
        :param name: name of the register
        :param value: value stored in the register
        :param clock: ClockProtocol
        :param last_update: last update time_stamp
        :param last_writer: SerializableType
        :param listeners: list[Callable[[UpdateProtocol], None
        :raises TypeError: name, value, clock, or last_writer
        """
        if clock is None:
            clock = LogicalClock()
        if last_update is None:
            last_update = clock.time_stamp
        if listeners is None:
            listeners = []

        self.name = name
        self.value = value
        self.clock = clock
        self.last_update = last_update
        self.last_writer = last_writer
        self.listeners = listeners

    def read(self) -> Hashable:
        """
        Return the eventually consistent data view.
        :return: SerializableType
        """
        return self.value

    @classmethod
    def compare_values(cls, left: Hashable, right: Hashable) -> bool:
        """
        True if left is greater than right, else False.
        :param left: value
        :param right: value
        :return: bool
        """
        return left > right

    def update(self, state_update: Update) -> LastWriterWinsRegister:
        """
        Apply an update.
        :param state_update: Update
        :return: LastWriterWinsRegister
        :raises ValueError: state_update invalid
        """
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")

        self.invoke_listeners(state_update)

        if self.clock.is_later(state_update.time_stamp, self.last_update):
            self.last_update = state_update.time_stamp
            self.last_writer = state_update.writer
            self.value = state_update.data
        elif self.clock.are_concurrent(state_update.time_stamp, self.last_update):
            if (
                self.last_writer is None
                or state_update.writer > self.last_writer
                or (
                    state_update.writer == self.last_writer
                    and self.compare_values(state_update.data, self.value)
                )
            ):
                self.last_writer = state_update.writer
                self.value = state_update.data

        self.clock.update()

        return self

    def checksum(
        self, /, *, from_time_stamp: float = None, until_time_stamp: float = None
    ) -> Tuple[int]:
        """
        Returns the hash for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: start time_stamp
        :param until_time_stamp: stop time_stamp
        :return: tuple[int]
        """
        return (hash(self.value),)

    def history(
        self, /, *, from_time_stamp: float = None, until_time_stamp: float = None
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
                data=self.value,
                update_type=None,
                writer=self.last_writer,
                name=None,
            ),
        )

    def write(self, value: Hashable, writer: Hashable) -> Update:
        """
        Writes the new value to the register and returns an Update by default. Requires a SerializableType
        writer id for tie breaking.
        :param value: value
        :param writer: writer
        :return: Update
        :raises TypeError: value or writer must be SerializableType
        """
        state_update = Update(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=value,
            update_type=None,
            writer=writer,
            name=None,
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


class LastWriterWinsMap(CRDT):
    """Last Writer Wins Map CRDT."""

    names: ObservedRemovedSet
    registers: Dict[Hashable, LastWriterWinsRegister]
    listeners: List[Callable]

    def __init__(
        self,
        names: ObservedRemovedSet = None,
        registers: Dict = None,
        listeners: List[Callable] = None,
    ) -> None:
        """
        Initialize an LastWriterWinsMap from an ObservedRemovedSet of names, a dict mapping
        names to LastWriterWinsRegisters, and a shared clock.
        :param names: ObservedRemovedSet
        :param registers: dict of names (keys) to LastWriterWinsRegisters (values)
        :param listeners: list[Callable]
        :raises TypeError: registers not filled with correct values (and/or types)
        """
        if listeners is None:
            listeners = []

        names = ObservedRemovedSet() if names is None else names
        registers = {} if registers is None else registers
        clock = LogicalClock()

        names.clock = clock

        for name in registers:
            registers[name].clock = clock

        self.names = names
        self.registers = registers
        self.clock = clock
        self.listeners = listeners

    def __getstate__(self):
        return self.__dict__.copy()

    def __setstate__(self, state):
        self.__dict__ = state

    def read(self) -> dict:
        """
        Return the eventually consistent data view.
        :return: dict
        """
        result = {}
        for name in self.names.read():
            if name in self.registers:
                result[name] = self.registers[name].read()
        return result

    def update(self, state_update: Update) -> LastWriterWinsMap:
        """
        Apply an update.
        :param state_update: Update
        :return: self (LastWriterWinsMap)
        :raises TypeError: invalid state_update data
        :raises ValueError: invalid state_update
        """
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")

        self.invoke_listeners(state_update)
        if state_update.update_type == UpdateType.Observed:
            self.names.update(
                Update(
                    clock_uuid=self.clock.uuid,
                    time_stamp=state_update.time_stamp,
                    data=state_update.name,
                    update_type=UpdateType.Observed,
                    writer=state_update.writer,
                    name=state_update.name,
                )
            )
            if (
                state_update.name not in self.registers
                and state_update.name in self.names.read()
            ):
                self.registers[state_update.name] = LastWriterWinsRegister(
                    state_update.name,
                    state_update.data,
                    self.clock,
                    state_update.time_stamp,
                    state_update.writer,
                )

        if state_update.update_type == UpdateType.Removed:
            self.names.update(
                Update(
                    self.clock.uuid,
                    state_update.time_stamp,
                    state_update.name,
                    UpdateType.Removed,
                    state_update.writer,
                    state_update.name,
                )
            )

            if (
                state_update.name not in self.names.read()
                and state_update.name in self.registers
            ):
                del self.registers[state_update.name]

        if state_update.name in self.registers:
            self.registers[state_update.name].update(
                Update(
                    self.clock.uuid,
                    state_update.time_stamp,
                    state_update.data,
                    state_update.update_type,
                    state_update.writer,
                    state_update.name,
                )
            )

        return self

    def checksum(
        self, /, *, from_time_stamp: float = None, until_time_stamp: float = None
    ) -> tuple[int, ...]:
        """
        Returns any checksums for the underlying data to detect de-synchronization due to message failure.
        :param from_time_stamp: unix timestamp
        :param until_time_stamp: unix timestamp
        :return: tuple[int]
        """
        results = []

        for name in self.registers:
            latest = self.registers[name].last_update
            if from_time_stamp is not None:
                if self.clock.is_later(from_time_stamp, latest):
                    continue
            if until_time_stamp is not None:
                if self.clock.is_later(latest, until_time_stamp):
                    continue
            results.append(self.registers[name].checksum()[0])

        return tuple(results)

    def history(
        self, /, *, from_time_stamp: float = None, until_time_stamp: float = None
    ) -> tuple[Update, ...]:
        """
        Returns a concise history of Updates that will converge to the underlying data. Useful for
        resynchronization by replaying updates from divergent nodes.
        :param from_time_stamp: unix timestamp
        :param until_time_stamp: unix timestamp
        :return: tuple[Update]
        """
        registers_history: dict[Hashable, tuple[Update]] = {}
        observed_removed_set_history = self.names.history(
            from_time_stamp=from_time_stamp, until_time_stamp=until_time_stamp
        )
        history = []

        for name in self.registers:
            registers_history[name] = self.registers[name].history(
                from_time_stamp=from_time_stamp, until_time_stamp=until_time_stamp
            )

        for update in observed_removed_set_history:
            if update.name in registers_history:
                register_update = registers_history[update.name][0]
                history.append(
                    Update(
                        clock_uuid=update.clock_uuid,
                        time_stamp=register_update.time_stamp,
                        data=register_update.data,
                        update_type=register_update.update_type,
                        writer=register_update.writer,
                        name=update.name,
                    )
                )
            else:
                history.append(
                    Update(
                        clock_uuid=update.clock_uuid,
                        time_stamp=update.time_stamp,
                        data=update.data,
                        update_type=update.update_type,
                        writer=update.writer,
                        name=update.name,
                    )
                )

        return tuple(history)

    def set(self, name: Hashable, value: Hashable, writer: Hashable) -> Update:
        """
        Extends the dict with name: value. Returns an Update that should be propagated to all nodes.
        :param name: Hashable
        :param value: value to store
        :param writer: hashable
        :return: Update
        """
        state_update = Update(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=value,
            update_type=UpdateType.Observed,
            writer=writer,
            name=name,
        )
        self.update(state_update)

        return state_update

    def unset(self, name: Hashable, writer: Hashable) -> Update:
        """
        Removes the key name from the dict.
        :param name: Hashable
        :param writer: SerializableType
        :return: Update
        """
        state_update = Update(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=None,
            update_type=UpdateType.Removed,
            writer=writer,
            name=name,
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


T = TypeVar("T", bound=CRDT)


class CRDTList(Generic[T]):
    """CRDTList behaves as a list of instances T that can be updated concurrently."""

    def __init__(
        self, content: List[T] = None, items: LastWriterWinsMap = None
    ) -> None:
        """
        Initialize from an LastWriterWinsMap of item positions and a shared clock if supplied otherwise default.
        :param content: list of T instances
        :param items: LastWriterWinsMap of T items
        """
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
        results = CRDTList[T]()
        for item in self:
            results.append(item.copy())
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
            iter([i for i, h in self.hardware.read() if h == item]),
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
        item = self.hardware.read()[index]
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
            iter([h for _, h in self.hardware.read() if h == item]),
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
        return len(self.hardware.read())

    def __eq__(self, other: CRDTList[T]) -> bool:
        return self.hardware.read() == other.hardware.read()

    def __ne__(self, other: CRDTList[T]) -> bool:
        return self.hardware.read() != other.hardware.read()

    def __contains__(self, item: T) -> bool:
        return item in self.hardware.read()

    def __delitem__(self, item: T) -> None:
        if item not in self.hardware.read():
            raise KeyError(f"{item} not found.")
        self.remove(item)

    def __getitem__(self, index: int) -> T:
        return self.hardware.read()[index]

    def __setitem__(self, index: int, value: T) -> None:
        self.hardware.set(index, value, hash(value))

    def __iter__(self) -> Iterable[T]:
        for _, item in self.hardware.read().items():
            yield item

    def __next__(self) -> T:
        if self.iterator >= len(self):
            self.iterator = 0
            raise StopIteration
        item = self.hardware.read()[self.iterator]
        self.iterator += 1
        return item

    def __add__(self, other: CRDTList[T]) -> CRDTList[T]:
        return self.extend(iter(other))

    def __sub__(self, other: CRDTList[T]) -> CRDTList[T]:
        for item in iter(other):
            self.remove(item)
        return self

    def __repr__(self) -> str:
        return f"HardwareList({self.hardware.read()})"

    def __reversed__(self) -> CRDTList[T]:
        return self.hardware.read()[::-1]

    def __sizeof__(self) -> int:
        return self.count()

    def __hash__(self):
        return hash(self.hardware)
