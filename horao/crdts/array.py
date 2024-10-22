from __future__ import annotations

from bisect import bisect
from decimal import Decimal
from typing import Any, Callable, Type
from uuid import uuid4

from packify import SerializableType, pack

from .clock import ScalarClock
from .data_types import Bytes, Float, FractionallyIndexedArrayItem
from .helpers import get_merkle_tree, resolve_merkle_tree
from .map import LastWriterWinsMap
from .protocols import Clock
from .update import Update


class FractionallyIndexedArray:
    """Fractionally-indexed array CRDT."""

    positions: LastWriterWinsMap
    clock: Clock
    store: list[FractionallyIndexedArrayItem]
    cache: list[SerializableType]
    listeners: list[Callable]

    def __init__(
        self,
        positions: LastWriterWinsMap = None,
        clock: Clock = None,
        listeners: list[Callable] = None,
    ) -> None:
        """
        Initialize from an LastWriterWinsMap of item positions and a shared clock.
        :param positions: LastWriterWinsMap of item positions
        :param clock: shared clock
        :param listeners: list of listeners
        """
        if listeners is None:
            listeners = []
        clock = ScalarClock() if clock is None else clock
        positions = LastWriterWinsMap(clock=clock) if positions is None else positions
        positions.clock = clock
        for name in positions.registers:
            positions.registers[name].clock = clock

        self.positions = positions
        self.clock = clock
        self.store = []
        self.cache = []
        self.listeners = listeners

    def pack(self) -> bytes:
        """
        Pack the data and metadata into a bytes string.
        :return: bytes
        """
        return self.positions.pack()

    @classmethod
    def unpack(cls, data: bytes, /, *, inject=None) -> FractionallyIndexedArray:
        """
        Unpack the data bytes string into an instance.
        :param data: serialized FractionallyIndexedArray needing unpacking
        :param inject: optional data to inject during unpacking
        :return: FractionallyIndexedArray
        """
        if inject is None:
            inject = {}
        positions = LastWriterWinsMap.unpack(data, inject)
        return cls(positions=positions, clock=positions.clock)

    def read(self, /, *, inject=None) -> tuple[Any, ...]:
        """
        Return the eventually consistent data view. Note: cannot be used for preparing deletion updates.
        :param inject: optional data to inject during unpacking
        :return: tuple[Any]
        """
        if inject is None:
            inject = {}
        if not self.cache:
            if not self.store:
                self.calculate(inject=inject)
            self.cache = [item.value for item in self.store]
        return tuple(self.cache)

    def read_full(self, /, *, inject=None) -> tuple[FractionallyIndexedArrayItem]:
        """
        Return the full, eventually consistent list of items without tombstones but with complete
        FractionallyIndexedArrayItem rather than the underlying SerializableType values. Use the
        resulting FractionallyIndexedArrayItem(s) for calling delete and move_item.
        (The FractionallyIndexedArrayItem containing a value put into the list will be index 3 of
        the Update returned by a put method.)
        :param inject: optional data to inject during unpacking
        :return: tuple[FractionallyIndexedArrayItem]
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        if not self.store:
            self.calculate(inject=inject)
        return tuple(self.store)

    def update(
        self, state_update: Update, /, *, inject=None
    ) -> FractionallyIndexedArray:
        """
        Apply an update (monad).
        :param state_update: update to apply
        :param inject: optional data to inject during unpacking
        :return: self
        :raises TypeError or ValueError for invalid state_update.
        """
        if inject is None:
            inject = {}
        if state_update.clock_uuid != self.clock.uuid:
            raise ValueError("state_update.clock_uuid must equal CRDT.clock.uuid")
        if type(state_update.data) is not tuple:
            raise TypeError("state_update.data must be tuple")
        if state_update.data[0] not in ("o", "r"):
            raise ValueError("state_update.data[0] must be in ('o', 'r')")
        if not isinstance(state_update.data[1], SerializableType):
            raise TypeError(
                f"state_update.data[1] must be SerializableType ({SerializableType})"
            )
        if not isinstance(state_update.data[2], SerializableType):
            raise TypeError(f"state_update.data[2] must be writer {SerializableType}")
        if not (
            isinstance(state_update.data[3], FractionallyIndexedArrayItem)
            or state_update.data[3] is None
        ):
            raise TypeError("state_update.data[3] must be FIAItemWrapper|None")

        self.invoke_listeners(state_update)
        self.positions.update(state_update)
        self.update_cache(
            state_update.data[1],
            state_update.data[3],
            state_update.data[0] == "o",
            inject=inject,
        )

        return self

    def checksums(
        self, /, *, from_time_stamp: Any = None, until_time_stamp: Any = None
    ) -> tuple[int]:
        """
        Returns checksums for the underlying data to detect de-synchronization due to partitioning.
        :param from_time_stamp: optional start time stamp
        :param until_time_stamp: optional stop time stamp
        :return: tuple[int]
        """
        return self.positions.checksums(
            from_time_stamp=from_time_stamp, until_time_stamp=until_time_stamp
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
        Returns a concise history of Updates that will converge to the underlying data.
        Useful for resynchronization by replaying all updates from divergent nodes.
        :param from_time_stamp: optional start time stamp
        :param until_time_stamp: optional stop time stamp
        :param update_class: type of update to use
        :return: tuple[Update]
        """
        return self.positions.history(
            from_time_stamp=from_time_stamp,
            until_time_stamp=until_time_stamp,
            update_class=update_class,
        )

    @classmethod
    def index_between(cls, first: Float, second: Float) -> Float:
        """
        Return an index between first and second with a random offset.
        :param first: first index
        :param second: second index
        :return: Decimal
        :raises TypeError: invalid first or second
        """
        return Float(first + second) / Float(2)

    def put(
        self,
        item: SerializableType,
        writer: SerializableType,
        index: Float,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Creates, applies, and returns an Update that puts the item at the index. The
        FractionallyIndexedArrayItem will be at index 3 of the data attribute of the returned update_class
        instance.
        :param item: item to put
        :param writer: writer id for tie breaking
        :param index: index for the item
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: Update
        """
        if inject is None:
            inject = {}
        fia_item = FractionallyIndexedArrayItem(
            value=item, index=index, uuid=uuid4().bytes
        )
        state_update = update_class(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=("o", Bytes(fia_item.uuid), writer, fia_item),
        )

        self.update(state_update, inject=inject)

        return state_update

    def put_between(
        self,
        item: SerializableType,
        writer: SerializableType,
        first: FractionallyIndexedArrayItem,
        second: FractionallyIndexedArrayItem,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Creates, applies, and returns an Update that puts the item at an index between first and
        second. The FractionallyIndexedArrayItem will be at index 3 of the data attribute of the returned update_class
        instance.
        :param item: item to put
        :param writer: writer id for tie breaking
        :param first: first item
        :param second: second item
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: Update
        """
        if inject is None:
            inject = {}
        first_index = first.index.value
        second_index = second.index.value
        index = self.index_between(first_index, second_index)

        return self.put(item, writer, index, update_class=update_class, inject=inject)

    def put_before(
        self,
        item: SerializableType,
        writer: SerializableType,
        other: FractionallyIndexedArrayItem,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Creates, applies, and returns an Update that puts the item before the other item. The
        FractionallyIndexedArrayItem will be at index 3 of the data attribute of the returned update_class instance.
        :param item: item to put
        :param writer: writer id for tie breaking
        :param other: item to put before
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: Update
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}

        before_index = other.index.value
        first_index = self.read_full(inject=inject).index(other)

        if first_index > 0:
            prior = self.read_full(inject=inject)[first_index - 1]
            prior_index = prior.index.value
        else:
            prior_index = Float(0)

        index = self.index_between(before_index, prior_index)

        return self.put(item, writer, index, update_class=update_class, inject=inject)

    def put_after(
        self,
        item: SerializableType,
        writer: SerializableType,
        other: FractionallyIndexedArrayItem,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Creates, applies, and returns an Update that puts the item after the other item. The
        FractionallyIndexedArrayItem will be at index 3 of the data attribute of the returned update_class instance.
        :param item: item to put
        :param writer: writer id for tie breaking
        :param other: item to put after
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: Update
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}

        after_index = other.index.value
        first_index = self.read_full(inject=inject).index(other)

        if len(self.read_full(inject=inject)) > first_index + 1:
            n = self.read_full(inject=inject)[first_index + 1]
            next_index = n.index.value
        else:
            next_index = Float(1)

        index = self.index_between(after_index, next_index)

        return self.put(item, writer, index, update_class=update_class, inject=inject)

    def put_first(
        self,
        item: SerializableType,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Creates, applies, and returns an Update that puts the item at an index between 0 and the
        first item. The FractionallyIndexedArrayItem will be at index 3 of the data attribute of the returned
        update_class instance.
        :param item: item to put
        :param writer: writer id for tie breaking
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: Update
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}
        if len(self.read_full(inject=inject)) > 0:
            first = self.read_full(inject=inject)[0]
            first_index = first.index.value
            index = Float(Float(0) + first_index) / Float(2)
        else:
            index = Float(0.5)
        return self.put(item, writer, index, update_class=update_class, inject=inject)

    def put_last(
        self,
        item: SerializableType,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Creates, applies, and returns an Update that puts the item at an index between the last
        item and 1. The FractionallyIndexedArrayItem will be at index 3 of the data attribute of the returned
        update_class instance.
        :param item: item to put
        :param writer: writer id for tie breaking
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: Update
        """
        if inject is None:
            inject = {}
        if len(self.read_full(inject=inject)) > 0:
            last = self.read_full(inject=inject)[-1]
            last_index = last.index.value
            index = Float(last_index + Float(1)) / Float(2)
        else:
            index = Float(0.5)
        return self.put(item, writer, index, update_class=update_class)

    def move_item(
        self,
        item: FractionallyIndexedArrayItem,
        writer: SerializableType,
        /,
        *,
        new_index: Float = None,
        after: FractionallyIndexedArrayItem = None,
        before: FractionallyIndexedArrayItem = None,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Creates, applies, and returns an Update that puts the item at the new index, or directly
        before the before, or directly after the after, or halfway between before and after. The
        FractionallyIndexedArrayItem will be at index 3 of the data attribute of the returned
        update_class instance.
        :param item: item to move
        :param writer: writer id for tie breaking
        :param new_index: new index for the item
        :param before: item to move before
        :param after: item to move after
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: Update
        """
        inject = {**globals(), **inject} if inject is not None else {**globals()}

        if item in self.store:
            self.store.remove(item)

        if new_index is None:
            if before and after:
                new_index = self.index_between(after.index.value, before.index.value)
            elif before:
                before_index = self.store.index(before)
                if before_index == 0:
                    new_index = self.index_between(Float("0"), before.index.value)
                else:
                    after = self.store[before_index - 1]
                    new_index = self.index_between(
                        after.index.value, before.index.value
                    )
            elif after:
                after_index = self.store.index(after)
                if after_index == len(self.store) - 1:
                    new_index = self.index_between(after.index.value, Float("1"))
                else:
                    before = self.store[after_index + 1]
                    new_index = self.index_between(
                        after.index.value, before.index.value
                    )

        item.index.value = new_index

        state_update = update_class(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=("o", Bytes(item.uuid), writer, item),
        )

        self.update(state_update, inject=inject)

        return state_update

    def normalize(
        self,
        writer: SerializableType,
        max_index: Float = Float("1.0"),
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> tuple[Update | Update, ...]:
        """
        Evenly distribute the item indices. Returns tuple of Update that encode
        the index updates. Applies each update as it is generated.
        :param writer: writer id for tie breaking
        :param max_index: maximum index value
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: tuple[Update]
        """
        if inject is None:
            inject = {}
        index_space = max_index / Float(len(self.read()) + 1)
        updates = []
        items = self.read_full()
        for i in range(len(items)):
            item = items[i]
            updates.append(
                self.move_item(
                    item,
                    writer,
                    new_index=index_space * Float(i),
                    update_class=update_class,
                    inject=inject,
                )
            )
        return tuple(updates)

    def normalize_list(
        self,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> tuple[Update]:
        """
        Calls normalize with a max_index calculated for use with the append method as
        the primary mechanism for adding to the list. Returns tuple of Update
        that encode the index updates. Applies each update as it is generated.
        :param writer: writer id for tie breaking
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: tuple[Update]
        """
        if inject is None:
            inject = {}
        max_index = Float("1E-20") * (1 + len(self.read()))
        return self.normalize(
            writer, max_index, update_class=update_class, inject=inject
        )

    def get_merkle_history(
        self, /, *, update_class: Type[Update] = Update
    ) -> list[bytes, list[bytes], dict[bytes, bytes]]:
        """
        Get a Merklized history for the Updates of the form [root, [content_id for update in self.history()],
        {content_id: packed for update in self.history()}] where packed is the result of update.pack()
        and content_id is the sha256 of the packed update.
        :param update_class: type of update to use
        :return: list[bytes, list[bytes], dict[bytes, bytes]]
        """
        return get_merkle_tree(self, update_class=update_class)

    def resolve_merkle_histories(
        self, history: list[bytes, list[bytes]]
    ) -> list[bytes]:
        """
        Accept a history of form [root, leaves] from another node.
        Return the leaves that need to be resolved and merged for synchronization.
        :param history: history to resolve
        :return: list[bytes]
        :raises TypeError: invalid history
        :raises ValueError: invalid history
        """
        return resolve_merkle_tree(self, tree=history)

    def index(self, item: SerializableType, _start: int = 0, _stop: int = None) -> int:
        """
        Returns the int index of the item in the list returned by read().
        :param item: item to find
        :param _start: optional start index
        :param _stop: optional stop index
        :return: int
        """
        if _stop:
            return self.read().index(item, _start, _stop)
        return self.read().index(item, _start)

    def append(
        self,
        item: SerializableType,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
    ) -> Update:
        """
        Creates, applies, and returns an Update that appends the item to
        the end of the list returned by read().
        :param item: item to append
        :param writer: writer id for tie breaking
        :param update_class: type of update to use
        :return: Update
        """
        full = self.read_full()
        last_index = full[-1].index.value if len(full) > 0 else Decimal(0)
        index = last_index + Decimal("1E-20")
        return self.put(item, writer, index, update_class=update_class)

    def remove(
        self,
        index: int,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
    ) -> Update:
        """
        Creates, applies, and returns an Update that removes the item at
        the index in the list returned by read().
        :param index: index of the item to remove
        :param writer: writer id for tie breaking
        :param update_class: type of update to use
        :return: Update
        :raises TypeError: invalid item or index
        """
        items = self.read_full()
        if 0 > index >= len(items):
            raise ValueError(f"index must be int between 0 and {len(items)-1}")
        item = items[index]
        return self.delete(item, writer, update_class=update_class)

    def delete(
        self,
        item: FractionallyIndexedArrayItem,
        writer: SerializableType,
        /,
        *,
        update_class: Type[Update] = Update,
        inject=None,
    ) -> Update:
        """
        Creates, applies, and returns an Update that deletes the item.
        Index 3 of the data attribute of the returned update_class instance will be the
        Nothing tombstone.
        :param item: item to delete
        :param writer: writer id for tie breaking
        :param update_class: type of update to use
        :param inject: optional data to inject during unpacking
        :return: Update
        """
        if inject is None:
            inject = {}
        state_update = update_class(
            clock_uuid=self.clock.uuid,
            time_stamp=self.clock.read(),
            data=("r", Bytes(item.uuid), writer, None),
        )
        self.update(state_update, inject=inject)
        return state_update

    def calculate(self, inject=None) -> None:
        """
        Reads the items from the underlying LastWriterWinsMap, orders them, then
        sets the cache_full list. Resets the cache.
        :param inject: optional data to inject during unpacking
        :return: None
        """
        if inject is None:
            inject = {}
        positions = self.positions.read(inject={**globals(), **inject})
        items: list[FractionallyIndexedArrayItem] = [v for k, v in positions.items()]
        items.sort(key=lambda item: (item.index.value, pack(item.value)))
        self.store = items
        self.cache = []

    def update_cache(
        self,
        uuid: Bytes,
        item: FractionallyIndexedArrayItem | None,
        visible: bool,
        /,
        *,
        inject=None,
    ) -> None:
        """
        Updates backing store by finding the correct insertion index for
        the given item, then inserting it there or removing it. Uses
        the bisect algorithm if necessary. Resets cache.
        :param uuid: UUID of the item to update
        :param item: item to insert or None to remove
        :param visible: whether the item should be visible in the list
        :param inject: optional data to inject during unpacking
        :return: None
        :raises TypeError: invalid item or visible
        """
        if inject is None:
            inject = {}

        positions = self.positions.read(inject={**globals(), **inject})

        if self.store is None:
            self.calculate(inject=inject)

        uuids = [i.uuid for i in self.store]
        try:
            index = uuids.index(uuid.value)
            del self.store[index]
        except BaseException:
            pass

        if visible and Bytes(item.uuid) in positions:
            # find correct insertion index
            # sort by (index, serialized value)
            index = bisect(
                self.store,
                (item.index.value, pack(item.value)),
                key=lambda a: (a.index.value, pack(a.value)),
            )
            self.store.insert(index, item)

        self.cache = []

    def add_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Adds a listener that is called on each update.
        :param listener: listener to add
        :return: None
        """
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Update], None]) -> None:
        """
        Removes a listener if it was previously added.
        :param listener: listener to remove
        :return: None
        """
        self.listeners.remove(listener)

    def invoke_listeners(self, state_update: Update) -> None:
        """
        Invokes all event listeners, passing them the state_update.
        :param state_update: update to pass to listeners
        :return: None
        """
        for listener in self.listeners:
            listener(state_update)
