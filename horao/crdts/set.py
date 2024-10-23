from __future__ import annotations

from binascii import crc32
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Type

from packify import SerializableType, pack, unpack

from .clock import ScalarClock
from .helpers import get_merkle_tree, resolve_merkle_tree
from .protocols import CRDT, Clock
from .update import Update


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
    clock: Clock = field(default_factory=ScalarClock)
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
    ) -> tuple[int]:
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
                update_class(
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
                update_class(
                    clock_uuid=self.clock.uuid,
                    time_stamp=self.removed_metadata[r],
                    data=("r", r),
                )
            )

        return tuple(updates)

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
        Accept a history of form [root, leaves] from another node. Return the leaves that need to be resolved
        and merged for synchronization.
        :param history: list[bytes, list[bytes]]
        :return: list[bytes]
        """
        return resolve_merkle_tree(self, tree=history)

    def observe(
        self, member: SerializableType, /, *, update_class: Type[Update] = Update
    ) -> Update:
        """
        Creates, applies, and returns an Update that adds the given member to the observed set. The
        member will be in the data attribute at index 1.
        :param member: SerializableType
        :param update_class: Type[Update]
        :return: Update
        :raises TypeError: member is not SerializableType
        """
        if not isinstance(member, SerializableType):
            raise TypeError(f"member must be SerializableType ({SerializableType})")

        state_update = update_class(
            clock_uuid=self.clock.uuid, time_stamp=self.clock.read(), data=("o", member)
        )

        self.update(state_update)

        return state_update

    def remove(
        self, member: SerializableType, /, *, update_class: Type[Update] = Update
    ) -> Update:
        """
        Creates, applies, and returns an Update that adds the given member to the removed set.
        :param member: SerializableType
        :param update_class: Type[Update]
        :return: Update
        """
        state_update = update_class(
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
