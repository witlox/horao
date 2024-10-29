from itertools import permutations

from horao.conceptual.crdt import (
    LastWriterWinsMap,
    LastWriterWinsRegister,
    ObservedRemovedSet,
)
from horao.conceptual.support import LogicalClock, Update


def test_lww_register_read_returns_value():
    lww_register = LastWriterWinsRegister("test", "foobar")
    assert lww_register.read() == "foobar"
    lww_register = LastWriterWinsRegister("test", "foobar")
    assert lww_register.read() == "foobar"


def test_lww_register_write_returns_state_update_and_sets_value():
    lww_register = LastWriterWinsRegister(b"test", b"foobar")
    lww_register.write(b"barfoo", 1)
    assert lww_register.read() == b"barfoo"


def test_lww_register_concurrent_writes_bias_to_higher_writer():
    lww_register1 = LastWriterWinsRegister("test")
    clock = LogicalClock(lww_register1.clock.time_stamp, lww_register1.clock.uuid)
    lww_register2 = LastWriterWinsRegister("test", clock=clock)

    update1 = lww_register1.write("foobar", b"1")
    update2 = lww_register2.write("barfoo", b"2")
    lww_register1.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read() == lww_register2.read()
    assert lww_register1.read() == "barfoo"


def test_lww_register_concurrent_writes_bias_to_one_value():
    lww_register1 = LastWriterWinsRegister("test")
    clock = LogicalClock(lww_register1.clock.time_stamp, lww_register1.clock.uuid)
    lww_register2 = LastWriterWinsRegister("test", clock=clock)

    update1 = lww_register1.write("foobar", [b"1", 2, "3"])
    update2 = lww_register2.write("barfoo", [b"1", 2, "2"])
    lww_register1.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read() == lww_register2.read()
    assert lww_register1.read() == "foobar"


def test_lww_register_checksums_returns_tuple_of_int():
    lww_register = LastWriterWinsRegister("test", "thing")
    assert lww_register.checksum() is not None


def test_lww_register_checksums_change_after_update():
    lww_register1 = LastWriterWinsRegister("test", "")
    clock = LogicalClock(lww_register1.clock.time_stamp, lww_register1.clock.uuid)
    lww_register2 = LastWriterWinsRegister("test", "", clock=clock)
    checksums1 = lww_register1.checksum()

    assert lww_register2.checksum() == checksums1

    lww_register1.write("foo", b"1")
    lww_register2.write("bar", b"2")

    assert lww_register1.checksum() != checksums1
    assert lww_register2.checksum() != checksums1
    assert lww_register1.checksum() != lww_register2.checksum()


def test_lww_register_update_is_idempotent():
    lww_register1 = LastWriterWinsRegister("test")
    clock1 = LogicalClock(lww_register1.clock.time_stamp, lww_register1.clock.uuid)
    lww_register2 = LastWriterWinsRegister("test", clock=clock1)

    update = lww_register1.write("foo", b"1")
    view1 = lww_register1.read()
    lww_register1.update(update)
    assert lww_register1.read() == view1
    lww_register2.update(update)
    view2 = lww_register2.read()
    lww_register2.update(update)
    assert lww_register2.read() == view2

    update = lww_register2.write("bar", b"2")
    lww_register1.update(update)
    view1 = lww_register1.read()
    lww_register1.update(update)
    assert lww_register1.read() == view1
    lww_register2.update(update)
    view2 = lww_register2.read()
    lww_register2.update(update)
    assert lww_register2.read() == view2


def test_lww_register_updates_are_commutative():
    lww_register1 = LastWriterWinsRegister("test")
    clock1 = LogicalClock(uuid=lww_register1.clock.uuid)
    lww_register2 = LastWriterWinsRegister("test", clock=clock1)

    update1 = lww_register1.write("foo1", b"1")
    update2 = lww_register1.write("foo2", b"1")
    lww_register2.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read() == lww_register2.read()


def test_lww_register_update_from_history_converges():
    lww_register1 = LastWriterWinsRegister("test")
    clock1 = LogicalClock(lww_register1.clock.time_stamp, lww_register1.clock.uuid)
    clock2 = LogicalClock(lww_register1.clock.time_stamp, lww_register1.clock.uuid)
    lww_register2 = LastWriterWinsRegister("test", clock=clock1)
    lww_register3 = LastWriterWinsRegister("test", clock=clock2)

    update = lww_register1.write("foo1", b"1")
    lww_register2.update(update)
    lww_register2.write("bar", b"2")

    for item in lww_register2.history():
        lww_register1.update(item)
        lww_register3.update(item)

    assert lww_register1.read() == lww_register2.read()
    assert lww_register1.read() == lww_register3.read()
    assert lww_register1.checksum() == lww_register2.checksum()
    assert lww_register1.checksum() == lww_register3.checksum()


def test_lww_register_history_return_value_determined_by_from_ts_and_until_ts():
    lww_register = LastWriterWinsRegister(name="test register")
    lww_register.write("first", 1)
    lww_register.write("second", 1)

    tomorrow = lww_register.clock.time_stamp + 86400
    yesterday = lww_register.clock.time_stamp - 86400

    assert len(lww_register.history(from_time_stamp=tomorrow)) == 0
    assert len(lww_register.history(until_time_stamp=yesterday)) == 0
    assert (
        len(lww_register.history(from_time_stamp=yesterday, until_time_stamp=tomorrow))
        == 1
    )


def test_lww_register_event_listeners_e2e():
    lww_register = LastWriterWinsRegister("test")
    logs = []

    def add_log(update: Update):
        logs.append(update)

    assert len(logs) == 0
    lww_register.write("value", "writer id")
    assert len(logs) == 0
    lww_register.add_listener(add_log)
    lww_register.write("value", "writer id")
    assert len(logs) == 1
    lww_register.remove_listener(add_log)
    lww_register.write("value", "writer id")
    assert len(logs) == 1


def test_or_set_read_returns_add_biased_set_difference():
    or_set = ObservedRemovedSet()
    assert or_set.read() == set()
    or_set.observe(1)
    or_set.observe(2)
    assert or_set.read() == {1, 2}
    or_set.remove(1)
    assert or_set.read() == {2}


def test_or_set_observe_and_remove_return_state_update():
    or_set = ObservedRemovedSet()
    update = or_set.observe(1)
    assert isinstance(update, Update)
    update = or_set.remove(1)
    assert isinstance(update, Update)


def test_or_set_history_returns_tuple_of_state_update():
    or_set = ObservedRemovedSet()
    or_set.observe(1)
    or_set.observe(2)
    history = or_set.history()
    assert type(history) is tuple
    for update in history:
        assert type(update) is Update


def test_or_set_read_returns_set_with_correct_values():
    or_set = ObservedRemovedSet()
    view1 = or_set.read()
    assert type(view1) is set
    assert len(view1) == 0
    or_set.observe(1)
    view2 = or_set.read()
    assert len(view2) == 1
    assert [*view2][0] == 1
    or_set.observe(2)
    view3 = or_set.read()
    assert len(view3) == 2
    assert 1 in view3
    assert 2 in view3
    or_set.remove(1)
    view4 = or_set.read()
    assert len(view4) == 1
    assert 2 in view4


def test_or_set_observe_and_remove_change_view():
    or_set = ObservedRemovedSet()
    view1 = or_set.read()
    or_set.observe(1)
    view2 = or_set.read()
    or_set.observe(2)
    view3 = or_set.read()
    or_set.remove(1)
    view4 = or_set.read()
    or_set.remove(5)
    view5 = or_set.read()
    assert view1 not in (view2, view3, view4, view5)
    assert view2 not in (view1, view3, view4, view5)
    assert view3 not in (view1, view2, view4, view5)
    assert view4 not in (view1, view2, view3)
    assert view4 == view5


def test_or_set_observe_and_remove_same_member_does_not_change_view():
    or_set = ObservedRemovedSet()
    or_set.observe(1)
    view1 = or_set.read()
    or_set.observe(1)
    view2 = or_set.read()
    assert view1 == view2
    or_set.observe(2)
    or_set.remove(1)
    view3 = or_set.read()
    or_set.remove(1)
    view4 = or_set.read()
    assert view3 == view4


def test_or_set_checksums_returns_tuple_of_int():
    or_set = ObservedRemovedSet()
    checksum = or_set.checksum()
    assert type(checksum) is tuple
    for item in checksum:
        assert type(item) is int


def test_or_set_checksums_change_after_update():
    or_set = ObservedRemovedSet()
    checksums1 = or_set.checksum()
    or_set.observe(1)
    checksums2 = or_set.checksum()
    or_set.remove(1)
    checksums3 = or_set.checksum()
    assert checksums1 != checksums2
    assert checksums2 != checksums3
    assert checksums3 != checksums1


def test_or_set_update_is_idempotent():
    or_set = ObservedRemovedSet()
    or_set = ObservedRemovedSet(clock=LogicalClock(0, or_set.clock.uuid))
    update = or_set.observe(2)
    view1 = or_set.read()
    or_set.update(update)
    assert or_set.read() == view1
    or_set.update(update)
    view2 = or_set.read()
    or_set.update(update)
    assert or_set.read() == view2 == view1

    update = or_set.remove(2)
    view1 = or_set.read()
    or_set.update(update)
    assert or_set.read() == view1
    or_set.update(update)
    view2 = or_set.read()
    or_set.update(update)
    assert or_set.read() == view2 == view1


def test_or_set_updates_from_history_converge():
    or_set1 = ObservedRemovedSet()
    or_set2 = ObservedRemovedSet(clock=LogicalClock(0, or_set1.clock.uuid))
    or_set1.observe(1)
    or_set1.remove(2)
    or_set1.observe(3)

    for update in or_set1.history():
        or_set2.update(update)

    assert or_set1.read() == or_set2.read()
    assert or_set1.checksum() == or_set2.checksum()

    histories = permutations(or_set1.history())
    for history in histories:
        or_set2 = ObservedRemovedSet(clock=LogicalClock(0, or_set1.clock.uuid))
        for update in history:
            or_set2.update(update)
        assert or_set2.read() == or_set1.read()
        assert or_set2.checksum() == or_set1.checksum()


def test_or_set_cache_is_set_upon_first_read():
    or_set = ObservedRemovedSet()
    or_set.observe(1)
    assert or_set.cache is None
    or_set.read()
    assert or_set.cache is not None


def test_or_set_convergence_from_ts():
    or_set1 = ObservedRemovedSet()
    or_set2 = ObservedRemovedSet()
    or_set2.clock.uuid = or_set1.clock.uuid
    for i in range(10):
        update = or_set1.observe(i)
        or_set2.update(update)
    assert or_set1.checksum() == or_set2.checksum()
    for i in range(5):
        update = or_set2.remove(i)
        or_set1.update(update)
    assert or_set1.checksum() == or_set2.checksum()

    or_set1.observe(303)
    or_set1.observe(202)
    or_set2.observe(101)

    from_ts = 0
    until_ts = or_set1.clock.read()
    while (
        or_set1.checksum(from_time_stamp=from_ts, until_time_stamp=until_ts)
        != or_set2.checksum(from_time_stamp=from_ts, until_time_stamp=until_ts)
        and until_ts > 0
    ):
        until_ts -= 1
    from_ts = until_ts
    assert from_ts > 0

    for update in or_set1.history(from_time_stamp=from_ts):
        or_set2.update(update)
    for update in or_set2.history(from_time_stamp=from_ts):
        or_set1.update(update)

    assert or_set1.checksum() == or_set2.checksum()

    or_set2 = ObservedRemovedSet()
    or_set2.clock.uuid = or_set1.clock.uuid
    for update in or_set1.history(until_time_stamp=0):
        or_set2.update(update)
    assert or_set1.checksum() != or_set2.checksum()

    or_set2 = ObservedRemovedSet()
    or_set2.clock.uuid = or_set1.clock.uuid
    for update in or_set1.history(from_time_stamp=99):
        or_set2.update(update)
    assert or_set1.checksum() != or_set2.checksum()


def test_or_set_event_listeners_e2e():
    or_set = ObservedRemovedSet()
    logs = []

    def add_log(update: Update):
        logs.append(update)

    assert len(logs) == 0
    or_set.observe("item")
    assert len(logs) == 0
    or_set.remove("item")
    assert len(logs) == 0
    or_set.add_listener(add_log)
    or_set.observe("item")
    assert len(logs) == 1
    or_set.remove("item")
    assert len(logs) == 2
    or_set.remove_listener(add_log)
    or_set.observe("item")
    assert len(logs) == 2
    or_set.remove("item")
    assert len(logs) == 2


def test_lww_map_read_after_extend_is_correct():
    lww_map = LastWriterWinsMap()
    view1 = lww_map.read()
    name = "foo"
    value = "bar"
    lww_map.set(name, value, 1)
    view2 = lww_map.read()
    assert view1 != view2
    assert name in view2
    assert view2[name] == value


def test_lww_map_read_after_unset_is_correct():
    lww_map = LastWriterWinsMap()
    name = "foo"
    value = "bar"
    lww_map.set(name, value, 1)
    view1 = lww_map.read()
    lww_map.unset(name, 1)
    view2 = lww_map.read()
    assert name in view1
    assert name not in view2


def test_lww_map_concurrent_writes_bias_to_higher_writer():
    lww_map = LastWriterWinsMap()
    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map.clock.uuid
    name = "foo"
    value1 = "bar"
    value2 = "test"
    update1 = lww_map.set(name, value1, 1)
    update2 = lww_map2.set(name, value2, 3)
    lww_map.update(update2)
    lww_map2.update(update1)

    assert lww_map.checksum() == lww_map2.checksum()
    assert lww_map.read()[name] == value2
    assert lww_map2.read()[name] == value2


def test_lww_map_checksums_change_after_update():
    lww_map = LastWriterWinsMap()
    lww_map.set("foo", "bar", 1)
    checksums1 = lww_map.checksum()
    lww_map.set("foo", "rab", 1)
    checksums2 = lww_map.checksum()
    lww_map.set("oof", "rab", 1)
    checksums3 = lww_map.checksum()

    assert checksums1 != checksums2
    assert checksums1 != checksums3
    assert checksums2 != checksums3


def test_lww_map_update_is_idempotent():
    lww_map = LastWriterWinsMap()
    update = lww_map.set("foo", "bar", 1)
    checksums1 = lww_map.checksum()
    view1 = lww_map.read()
    lww_map.update(update)
    checksums2 = lww_map.checksum()
    view2 = lww_map.read()

    assert checksums1 == checksums2
    assert view1 == view2


def test_lww_map_event_listeners_e2e():
    lww_map = LastWriterWinsMap()
    logs = []

    def add_log(update: Update):
        logs.append(update)

    assert len(logs) == 0
    lww_map.set("name", "value", "writer id")
    assert len(logs) == 0
    lww_map.add_listener(add_log)
    lww_map.set("name", "value", "writer id")
    assert len(logs) == 1
    lww_map.remove_listener(add_log)
    lww_map.set("name", "value", "writer id")
    assert len(logs) == 1
