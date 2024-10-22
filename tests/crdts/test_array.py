from decimal import Decimal
from itertools import permutations
from uuid import uuid4

import packify

from horao.crdts import Update
from horao.crdts.array import FractionallyIndexedArray
from horao.crdts.clock import ScalarClock, StringClock
from horao.crdts.data_types import (
    Bytes,
    ComplexType,
    Float,
    FractionallyIndexedArrayItem,
    Integer,
    Nothing,
    ReplicatedGrowableArrayItem,
    String,
)

inject = {
    "Bytes": Bytes,
    "String": String,
    "Integer": Integer,
    "Float": Float,
    "ComplexType": ComplexType,
    "ReplicatedGrowableArrayItem": ReplicatedGrowableArrayItem,
    "FractionallyIndexedArrayItem": FractionallyIndexedArrayItem,
    "Nothing": Nothing,
    "ScalarClock": ScalarClock,
}


def test_array_append_returns_state_update_protocol_and_changes_read():
    fia = FractionallyIndexedArray()
    view1 = fia.read()

    item = b"hello"
    state_update = fia.append(item, 1)
    assert isinstance(state_update, Update)

    view2 = fia.read()
    assert view1 != view2
    assert view2[0] == item


def test_array_index_returns_int():
    fia = FractionallyIndexedArray()
    fia.append("item1", 123)
    fia.append("item2", 123)
    assert fia.index("item1") == 0
    assert fia.index("item2") == 1


def test_array_remove_returns_state_update_protocol_and_changes_read():
    fia = FractionallyIndexedArray()
    fia.append("item1", 123)
    fia.append("item2", 123)
    view = fia.read()
    assert "item1" in view
    index = fia.index("item1")
    state_update = fia.remove(index, 123)
    assert fia.read() != view
    assert "item1" not in fia.read()


def test_array_read_returns_tuple_of_underlying_items():
    fi_array = FractionallyIndexedArray()
    first = FractionallyIndexedArrayItem(
        value="first",
        index=Float(0.1),
        uuid=uuid4().bytes,
    )
    second = FractionallyIndexedArrayItem(
        value=b"second",
        index=Float(0.2),
        uuid=uuid4().bytes,
    )
    fi_array.positions.set(Bytes(first.uuid), first, 1)
    fi_array.positions.set(Bytes(second.uuid), second, 1)
    view = fi_array.read()
    assert isinstance(view, tuple)
    assert view == ("first", b"second")


def test_array_read_full_returns_tuple_of_FIAItemWrapper():
    fi_array = FractionallyIndexedArray()
    first = FractionallyIndexedArrayItem(
        value="first",
        index=Float(0.1),
        uuid=uuid4().bytes,
    )
    second = FractionallyIndexedArrayItem(
        value=b"second",
        index=Float(0.2),
        uuid=uuid4().bytes,
    )
    fi_array.positions.set(Bytes(first.uuid), first, 1)
    fi_array.positions.set(Bytes(second.uuid), second, 1)
    view = fi_array.read_full()

    assert isinstance(view, tuple)
    assert len(view) == 2

    for item in view:
        assert isinstance(item, FractionallyIndexedArrayItem)

    assert view[0].value == "first"
    assert view[1].value == b"second"


def test_array_index_between_returns_between_first_and_second():
    first = Float(0.10001)
    second = Float(0.10002)
    index = FractionallyIndexedArray.index_between(first, second)

    assert index > first
    assert index < second


def test_array_put_returns_update_with_tuple():
    fi_array = FractionallyIndexedArray()
    update = fi_array.put(String("test"), 1, Float(0.5))

    assert type(update.data) is tuple
    assert len(update.data) == 4
    assert update.data[0] == "o"
    assert update.data[2] == 1
    assert update.data[3].index == Float(0.5)


def test_array_put_changes_view():
    fi_array = FractionallyIndexedArray()
    view1 = fi_array.read(inject=inject)
    fi_array.put(String("test"), 1, Float(0.5))
    view2 = fi_array.read(inject=inject)

    assert view1 != view2


def test_array_put_results_in_correct_order_read():
    fi_array = FractionallyIndexedArray()
    fi_array.put("test", 1, Float(0.5))
    fi_array.put("foo", 1, Float(0.25))
    fi_array.put("bar", 1, Float(0.375))
    view = fi_array.read()

    assert len(view) == 3
    assert view[0] == "foo"
    assert view[1] == "bar"
    assert view[2] == "test"


def test_array_put_between_results_in_correct_order_read():
    fi_array = FractionallyIndexedArray()
    first = fi_array.put("first", 1, Float(0.5)).data[3]
    last = fi_array.put("last", 1, Float(0.75)).data[3]
    update = fi_array.put_between("middle", 1, first, last)
    view = fi_array.read()

    assert type(update) is Update
    assert len(view) == 3
    assert view[0] == "first"
    assert view[1] == "middle"
    assert view[2] == "last"


def test_array_put_before_results_in_correct_order_read():
    fi_array = FractionallyIndexedArray()
    fi_array.put(("last"), 1, Float(0.5))
    middle = fi_array.put(("middle"), 1, Float(0.25)).data[3]
    update = fi_array.put_before("first", 1, middle)
    view = fi_array.read()

    assert type(update) is Update
    assert len(view) == 3
    assert view[0] == "first"
    assert view[1] == "middle"
    assert view[2] == "last"


def test_array_put_after_results_in_correct_order_read():
    fi_array = FractionallyIndexedArray()
    fi_array.put(("first"), 1, Float(0.5))
    middle = fi_array.put(("middle"), 1, Float(0.75)).data[3]
    update = fi_array.put_after(("last"), 1, middle)
    view = fi_array.read()

    assert type(update) is Update
    assert len(view) == 3
    assert view[0] == "first"
    assert view[1] == "middle"
    assert view[2] == "last"


def test_array_put_first_results_in_correct_order_read():
    fi_array = FractionallyIndexedArray()
    fi_array.put_first("test", 1)
    fi_array.put_first("bar", 1)
    update = fi_array.put_first("foo", 1)
    view = fi_array.read()

    assert type(update) is Update
    assert len(view) == 3
    assert view[0] == "foo"
    assert view[1] == "bar"
    assert view[2] == "test"


def test_array_put_last_results_in_correct_order_read():
    fi_array = FractionallyIndexedArray()
    fi_array.put_last(String("foo"), 1)
    fi_array.put_last(String("bar"), 1)
    fi_array.put_last(String("test"), 1)
    view = fi_array.read_full()

    assert len(view) == 3
    assert view[0].value == String("foo")
    assert view[1].value == String("bar")
    assert view[2].value == String("test")


def test_array_delete_returns_state_update_with_tuple():
    fi_array = FractionallyIndexedArray()
    first = fi_array.put_first("test", 1).data[3]
    update = fi_array.delete(first, 1)

    assert type(update) is Update
    assert type(update.data) is tuple
    assert len(update.data) == 4
    assert update.data[0] == "r"
    assert isinstance(update.data[1], Bytes)
    assert update.data[2] == 1
    assert update.data[3] is None


def test_array_delete_removes_item():
    fi_array = FractionallyIndexedArray()
    first = fi_array.put_first(("test"), 1).data[3]

    assert fi_array.read()[0] == "test"
    fi_array.delete(first, 1)
    assert fi_array.read() == tuple()


def test_array_move_item_returns_state_update_and_moves_item_to_new_index():
    fi_array = FractionallyIndexedArray()
    second = fi_array.put("second", 1, Float(0.5)).data[3]
    first = fi_array.put_after("first", 1, second).data[3]
    third = fi_array.put_first("third", 1).data[3]
    assert fi_array.read() == ("third", "second", "first")

    update = fi_array.move_item(first, 1, before=third)
    assert isinstance(update, Update)
    assert fi_array.read() == ("first", "third", "second")

    fi_array.move_item(first, 1, after=second)
    assert fi_array.read() == ("third", "second", "first")

    fi_array.move_item(first, 1, new_index=Float(0.1))
    assert fi_array.read() == ("first", "third", "second")

    fi_array.move_item(second, 1, after=first, before=third)
    assert fi_array.read() == ("first", "second", "third")


def test_array_history_returns_tuple_of_state_update_protocol():
    fi_array = FractionallyIndexedArray()
    fi_array.put_first(String("test"), 1)
    fi_array.put_first(String("fdfdf"), 1)
    history = fi_array.history()

    assert type(history) is tuple
    for update in history:
        assert isinstance(update, Update)


def test_array_concurrent_puts_bias_to_higher_writer():
    fi_array1 = FractionallyIndexedArray()
    fi_array2 = FractionallyIndexedArray(clock=ScalarClock(uuid=fi_array1.clock.uuid))
    update1 = fi_array1.put(String("test"), 1, Float(0.75))
    update2 = fi_array2.put(("test"), 2, Float(0.25))
    update3 = fi_array1.put(String("middle"), 1, Float(0.5))
    fi_array1.update(update2)
    fi_array2.update(update1)
    fi_array2.update(update3)

    assert fi_array1.checksums() == fi_array2.checksums()
    assert fi_array1.read()[0] == "test"


def test_array_checksums_returns_tuple_of_int():
    fi_array = FractionallyIndexedArray()
    fi_array.put(String("foo"), 1, Float(0.25))
    checksums = fi_array.checksums()

    assert type(checksums) is tuple
    for item in checksums:
        assert type(item) is int


def test_array_checksums_change_after_update():
    fi_array = FractionallyIndexedArray()
    fi_array.put(String("foo"), 1, Float(0.25))
    checksums1 = fi_array.checksums()
    fi_array.put(String("foo"), 1, Float(0.5))
    checksums2 = fi_array.checksums()
    fi_array.put(String("oof"), 1, Float(0.35))
    checksums3 = fi_array.checksums()

    assert checksums1 != checksums2
    assert checksums1 != checksums3
    assert checksums2 != checksums3


def test_array_update_is_idempotent():
    fi_array = FractionallyIndexedArray()
    update = fi_array.put(String("foo"), 1, Float(0.25))
    checksums1 = fi_array.checksums()
    view1 = fi_array.read()
    fi_array.update(update)
    checksums2 = fi_array.checksums()
    view2 = fi_array.read()

    assert checksums1 == checksums2
    assert view1 == view2


def test_array_updates_are_commutative():
    fi_array1 = FractionallyIndexedArray()
    fi_array2 = FractionallyIndexedArray(clock=ScalarClock(0, fi_array1.clock.uuid))
    fi_array3 = FractionallyIndexedArray(clock=ScalarClock(0, fi_array1.clock.uuid))
    update1 = fi_array1.put(String("test"), 1, Float(0.75))
    update2 = fi_array1.put(String("test"), 2, Float(0.25))
    update3 = fi_array1.put(String("middle"), 1, Float(0.5))

    fi_array2.update(update1)
    fi_array2.update(update2)
    fi_array2.update(update3)
    fi_array3.update(update3)
    fi_array3.update(update2)
    fi_array3.update(update1)

    assert fi_array1.read() == fi_array2.read() == fi_array3.read()


def test_array_converges_from_history():
    fi_array1 = FractionallyIndexedArray()
    fi_array2 = FractionallyIndexedArray(clock=ScalarClock(0, fi_array1.clock.uuid))
    fi_array1.put(String("foo"), 1, Float(0.25))
    item = fi_array1.put(String("test"), 1, Float(0.15)).data[3]
    fi_array1.put(String("bar"), 1, Float(0.5))

    for state_update in fi_array2.history():
        fi_array1.update(state_update)
    for state_update in fi_array1.history():
        fi_array2.update(state_update)

    fi_array2.delete(item, 1)
    fi_array2.put(String("something"), 2, Float(0.333))
    fi_array2.put(String("something else"), 2, Float(0.777))

    for state_update in fi_array1.history():
        fi_array2.update(state_update)
    for state_update in fi_array2.history():
        fi_array1.update(state_update)

    view1 = fi_array1.read()
    view2 = fi_array2.read()
    assert view1 == view2, f"{view1} != {view2}"

    histories = permutations(fi_array1.history())
    for history in histories:
        fi_array3 = FractionallyIndexedArray(clock=ScalarClock(0, fi_array1.clock.uuid))
        for update in history:
            fi_array3.update(update)
        view3 = fi_array3.read()
        assert view3 == view1, f"{view3} != {view1}"


def test_array_pack_unpack_e2e():
    fi_array = FractionallyIndexedArray()
    fi_array.put_first(String("test"), 1)
    fi_array.put_last(Bytes(b"test"), 1)
    packed = fi_array.pack()
    unpacked = FractionallyIndexedArray.unpack(packed, inject=inject)

    assert fi_array.checksums() == unpacked.checksums()
    assert fi_array.read() == unpacked.read()

    update = unpacked.put_last(String("middle"), 2)
    fi_array.update(update)

    assert fi_array.checksums() == unpacked.checksums()
    assert fi_array.read() == unpacked.read()


def test_array_pack_unpack_e2e_with_injected_clock():
    fia = FractionallyIndexedArray(clock=StringClock())
    fia.put_first(String("first"), 1)
    fia.put_last(String("last"), 1)
    packed = fia.pack()

    unpacked = FractionallyIndexedArray.unpack(
        packed, inject={**inject, "StringClock": StringClock}
    )

    assert unpacked.clock == fia.clock
    assert unpacked.read() == fia.read()


def test_array_convergence_from_ts():
    fi_array1 = FractionallyIndexedArray()
    fi_array2 = FractionallyIndexedArray()
    fi_array2.clock.uuid = fi_array1.clock.uuid
    for i in range(5):
        update = fi_array2.put_first(Integer(i), i)
        fi_array1.update(update)
    assert fi_array1.checksums() == fi_array2.checksums()

    fi_array1.put_last(Integer(69420), 1)
    fi_array1.put_last(Integer(42069), 1)
    fi_array2.put_last(Integer(23212), 2)

    from_ts = 0
    until_ts = fi_array1.clock.read()
    while (
        fi_array1.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
        != fi_array2.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
        and until_ts > 0
    ):
        until_ts -= 1
    from_ts = until_ts
    assert from_ts > 0

    for update in fi_array1.history(from_time_stamp=from_ts):
        fi_array2.update(update)
    for update in fi_array2.history(from_time_stamp=from_ts):
        fi_array1.update(update)

    assert fi_array1.checksums() == fi_array2.checksums()

    fi_array2 = FractionallyIndexedArray()
    fi_array2.clock.uuid = fi_array1.clock.uuid
    for update in fi_array1.history(until_time_stamp=0):
        fi_array2.update(update)
    assert fi_array1.checksums() != fi_array2.checksums()

    fi_array2 = FractionallyIndexedArray()
    fi_array2.clock.uuid = fi_array1.clock.uuid
    for update in fi_array1.history(from_time_stamp=99):
        fi_array2.update(update)
    assert fi_array1.checksums() != fi_array2.checksums()


def test_array_normalize_evenly_spaces_existing_items():
    fia = FractionallyIndexedArray()
    fia.put("first", 1, Float(0.9))
    fia.put("second", 1, Float(0.91))
    fia.put("third", 1, Float(0.92))
    assert fia.read() == ("first", "second", "third")

    sus = fia.normalize(1)
    assert type(sus) is tuple
    for su in sus:
        assert isinstance(su, Update)

    assert fia.read() == ("first", "second", "third")
    indices = [f.index.value for f in fia.read_full()]
    index_space = Float(1) / Float(4)

    for i in range(len(indices)):
        assert indices[i] == index_space * Float(i)


def test_array_merkle_history_e2e():
    fia1 = FractionallyIndexedArray()
    fia2 = FractionallyIndexedArray(clock=ScalarClock(0, fia1.clock.uuid))
    fia2.update(fia1.put_first("hello world", 1))
    fia2.update(fia1.put_last(b"hello world", 1))
    fia1.delete(fia1.read_full()[0], 1)
    fia1.put_last("hello", 1)
    fia2.put_last(b"world", 2)

    history1 = fia1.get_merkle_history()
    history2 = fia2.get_merkle_history()
    cidmap1 = history1[2]
    cidmap2 = history2[2]

    diff1 = fia1.resolve_merkle_histories(history2)
    diff2 = fia2.resolve_merkle_histories(history1)
    assert len(diff1) == 2, [d.hex() for d in diff1]
    assert len(diff2) == 2, [d.hex() for d in diff2]
    for cid in diff1:
        update = Update.unpack(cidmap2[cid], inject=inject)
        fia1.update(update)
    for cid in diff2:
        update = Update.unpack(cidmap1[cid], inject=inject)
        fia2.update(update)

    assert (
        fia1.checksums() == fia2.checksums()
    ), f"\n{fia1.read_full()}\n{fia2.read_full()}"


def test_array_event_listeners_e2e():
    fia = FractionallyIndexedArray()
    logs = []

    def add_log(update: Update):
        logs.append(update)

    assert len(logs) == 0
    fia.put_first("item", "writer id")
    assert len(logs) == 0
    fia.add_listener(add_log)
    fia.put_first("item", "writer id")
    assert len(logs) == 1
    fia.put_after("item", "writer id", fia.read_full()[0])
    assert len(logs) == 2
    fia.remove_listener(add_log)
    fia.put_first("item", "writer id")
    assert len(logs) == 2
