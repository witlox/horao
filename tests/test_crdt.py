from itertools import permutations

from horao.models.crdt import (
    LastWriterWinsMap,
    LastWriterWinsRegister,
    ObservedRemovedSet,
)
from horao.models.internal import LogicalClock, Update


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


def test_lww_register_merkle_history_e2e():
    lww_register1 = LastWriterWinsRegister("test")
    lww_register2 = LastWriterWinsRegister(
        "test", clock=LogicalClock(0, lww_register1.clock.uuid)
    )
    lww_register2.update(lww_register1.write("hello world", 1))
    lww_register2.update(lww_register1.write(b"hello world", 1))
    lww_register1.write("hello world", 1)
    lww_register1.write("hello", 1)
    lww_register2.write(b"world", 2)

    history1 = lww_register1.get_merkle_history()
    history2 = lww_register2.get_merkle_history()
    cidmap1 = history1[2]
    cidmap2 = history2[2]

    diff1 = lww_register1.resolve_merkle_histories(history2)
    diff2 = lww_register2.resolve_merkle_histories(history1)
    assert len(diff1) == 1, [d.hex() for d in diff1]
    assert len(diff2) == 1, [d.hex() for d in diff2]

    for cid in diff1:
        lww_register1.update(Update.unpack(cidmap2[cid]))
    for cid in diff2:
        lww_register2.update(Update.unpack(cidmap1[cid]))

    assert lww_register1.checksum() == lww_register2.checksum()


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
    orset = ObservedRemovedSet()
    assert orset.read() == set()
    orset.observe(1)
    orset.observe(2)
    assert orset.read() == {1, 2}
    orset.remove(1)
    assert orset.read() == {2}


def test_or_set_observe_and_remove_return_state_update():
    orset = ObservedRemovedSet()
    update = orset.observe(1)
    assert isinstance(update, Update)
    update = orset.remove(1)
    assert isinstance(update, Update)


def test_or_set_history_returns_tuple_of_state_update():
    orset = ObservedRemovedSet()
    orset.observe(1)
    orset.observe(2)
    history = orset.history()
    assert type(history) is tuple
    for update in history:
        assert type(update) is Update


def test_or_set_read_returns_set_with_correct_values():
    orset = ObservedRemovedSet()
    view1 = orset.read()
    assert type(view1) is set
    assert len(view1) == 0
    orset.observe(1)
    view2 = orset.read()
    assert len(view2) == 1
    assert [*view2][0] == 1
    orset.observe(2)
    view3 = orset.read()
    assert len(view3) == 2
    assert 1 in view3
    assert 2 in view3
    orset.remove(1)
    view4 = orset.read()
    assert len(view4) == 1
    assert 2 in view4


def test_or_set_observe_and_remove_change_view():
    orset = ObservedRemovedSet()
    view1 = orset.read()
    orset.observe(1)
    view2 = orset.read()
    orset.observe(2)
    view3 = orset.read()
    orset.remove(1)
    view4 = orset.read()
    orset.remove(5)
    view5 = orset.read()
    assert view1 not in (view2, view3, view4, view5)
    assert view2 not in (view1, view3, view4, view5)
    assert view3 not in (view1, view2, view4, view5)
    assert view4 not in (view1, view2, view3)
    assert view4 == view5


def test_or_set_observe_and_remove_same_member_does_not_change_view():
    orset = ObservedRemovedSet()
    orset.observe(1)
    view1 = orset.read()
    orset.observe(1)
    view2 = orset.read()
    assert view1 == view2
    orset.observe(2)
    orset.remove(1)
    view3 = orset.read()
    orset.remove(1)
    view4 = orset.read()
    assert view3 == view4


def test_or_set_checksums_returns_tuple_of_int():
    orset = ObservedRemovedSet()
    checksum = orset.checksum()
    assert type(checksum) is tuple
    for item in checksum:
        assert type(item) is int


def test_or_set_checksums_change_after_update():
    orset = ObservedRemovedSet()
    checksums1 = orset.checksum()
    orset.observe(1)
    checksums2 = orset.checksum()
    orset.remove(1)
    checksums3 = orset.checksum()
    assert checksums1 != checksums2
    assert checksums2 != checksums3
    assert checksums3 != checksums1


def test_or_set_update_is_idempotent():
    orset1 = ObservedRemovedSet()
    orset2 = ObservedRemovedSet(clock=LogicalClock(0, orset1.clock.uuid))
    update = orset1.observe(2)
    view1 = orset1.read()
    orset1.update(update)
    assert orset1.read() == view1
    orset2.update(update)
    view2 = orset2.read()
    orset2.update(update)
    assert orset2.read() == view2 == view1

    update = orset1.remove(2)
    view1 = orset1.read()
    orset1.update(update)
    assert orset1.read() == view1
    orset2.update(update)
    view2 = orset2.read()
    orset2.update(update)
    assert orset2.read() == view2 == view1


def test_or_set_updates_from_history_converge():
    orset1 = ObservedRemovedSet()
    orset2 = ObservedRemovedSet(clock=LogicalClock(0, orset1.clock.uuid))
    orset1.observe(1)
    orset1.remove(2)
    orset1.observe(3)

    for update in orset1.history():
        orset2.update(update)

    assert orset1.read() == orset2.read()
    assert orset1.checksum() == orset2.checksum()

    histories = permutations(orset1.history())
    for history in histories:
        orset2 = ObservedRemovedSet(clock=LogicalClock(0, orset1.clock.uuid))
        for update in history:
            orset2.update(update)
        assert orset2.read() == orset1.read()
        assert orset2.checksum() == orset1.checksum()


def test_or_set_pack_unpack_e2e():
    orset1 = ObservedRemovedSet()
    orset1.observe(1)
    orset1.observe("hello")
    orset1.remove(2)
    orset1.remove(b"hello")
    packed = orset1.pack()
    orset2 = ObservedRemovedSet.unpack(packed)

    assert orset1.clock.uuid == orset2.clock.uuid
    assert orset1.read() == orset2.read()
    assert orset1.checksum() == orset2.checksum()
    assert orset1.history() in permutations(orset2.history())


def test_or_set_cache_is_set_upon_first_read():
    orset = ObservedRemovedSet()
    orset.observe(1)
    assert orset.cache is None
    orset.read()
    assert orset.cache is not None


def test_or_set_convergence_from_ts():
    orset1 = ObservedRemovedSet()
    orset2 = ObservedRemovedSet()
    orset2.clock.uuid = orset1.clock.uuid
    for i in range(10):
        update = orset1.observe(i)
        orset2.update(update)
    assert orset1.checksum() == orset2.checksum()
    for i in range(5):
        update = orset2.remove(i)
        orset1.update(update)
    assert orset1.checksum() == orset2.checksum()

    orset1.observe(69420)
    orset1.observe(42096)
    orset2.observe(23878)

    # not the most efficient algorithm, but it demonstrates the concept
    from_ts = 0
    until_ts = orset1.clock.read()
    while (
        orset1.checksum(from_time_stamp=from_ts, until_time_stamp=until_ts)
        != orset2.checksum(from_time_stamp=from_ts, until_time_stamp=until_ts)
        and until_ts > 0
    ):
        until_ts -= 1
    from_ts = until_ts
    assert from_ts > 0

    for update in orset1.history(from_time_stamp=from_ts):
        orset2.update(update)
    for update in orset2.history(from_time_stamp=from_ts):
        orset1.update(update)

    assert orset1.checksum() == orset2.checksum()

    orset2 = ObservedRemovedSet()
    orset2.clock.uuid = orset1.clock.uuid
    for update in orset1.history(until_time_stamp=0):
        orset2.update(update)
    assert orset1.checksum() != orset2.checksum()

    orset2 = ObservedRemovedSet()
    orset2.clock.uuid = orset1.clock.uuid
    for update in orset1.history(from_time_stamp=99):
        orset2.update(update)
    assert orset1.checksum() != orset2.checksum()


def test_or_set_merkle_history_e2e():
    ors1 = ObservedRemovedSet()
    ors2 = ObservedRemovedSet(clock=LogicalClock(0, ors1.clock.uuid))
    ors2.update(ors1.observe("hello world"))
    ors2.update(ors1.observe(b"hello world"))
    ors1.remove("hello world")
    ors1.observe("abra")
    ors2.observe(b"cadabra")

    history1 = ors1.get_merkle_history()
    history2 = ors2.get_merkle_history()
    cidmap1 = history1[2]
    cidmap2 = history2[2]

    diff1 = ors1.resolve_merkle_histories(history2)
    diff2 = ors2.resolve_merkle_histories(history1)
    assert len(diff1) == 2, [d.hex() for d in diff1]
    assert len(diff2) == 2, [d.hex() for d in diff2]

    for cid in diff1:
        update = Update.unpack(cidmap2[cid])
        ors1.update(update)
    for cid in diff2:
        update = Update.unpack(cidmap1[cid])
        ors2.update(update)

    assert ors1.get_merkle_history() == ors2.get_merkle_history()
    assert ors1.checksum() == ors2.checksum()


def test_or_set_event_listeners_e2e():
    orset = ObservedRemovedSet()
    logs = []

    def add_log(update: Update):
        logs.append(update)

    assert len(logs) == 0
    orset.observe("item")
    assert len(logs) == 0
    orset.remove("item")
    assert len(logs) == 0
    orset.add_listener(add_log)
    orset.observe("item")
    assert len(logs) == 1
    orset.remove("item")
    assert len(logs) == 2
    orset.remove_listener(add_log)
    orset.observe("item")
    assert len(logs) == 2
    orset.remove("item")
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


def test_lww_map_pack_unpack_e2e():
    lww_map = LastWriterWinsMap()
    lww_map.set("foo", "bar", 1)
    lww_map.set("foo", "rab", 1)
    lww_map.set("foof", "barb", 1)
    lww_map.unset("foof", 1)
    lww_map.set("oof", "rab", 1)
    packed = lww_map.pack()
    unpacked = LastWriterWinsMap.unpack(packed)

    assert unpacked.checksum() == lww_map.checksum()


def test_lww_map_convergence_from_ts():
    lww_map1 = LastWriterWinsMap()
    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map1.clock.uuid
    for i in range(10):
        update = lww_map1.set(i, i, 1)
        lww_map2.update(update)
    assert lww_map1.checksum() == lww_map2.checksum()

    lww_map1.set(69420, 69420, 1)
    lww_map1.set(42096, 42096, 1)
    lww_map2.set(23878, 23878, 2)

    # not the most efficient algorithm, but it demonstrates the concept
    from_ts = 0
    until_ts = lww_map1.clock.read()
    chksm1 = lww_map1.checksum(from_time_stamp=from_ts, until_time_stamp=until_ts)
    chksm2 = lww_map2.checksum(from_time_stamp=from_ts, until_time_stamp=until_ts)
    while chksm1 != chksm2 and until_ts > 0:
        until_ts -= 1
        chksm1 = lww_map1.checksum(from_time_stamp=from_ts, until_time_stamp=until_ts)
        chksm2 = lww_map2.checksum(from_time_stamp=from_ts, until_time_stamp=until_ts)
    from_ts = until_ts
    assert from_ts > 0

    for update in lww_map1.history(from_time_stamp=from_ts):
        lww_map2.update(update)
    for update in lww_map2.history(from_time_stamp=from_ts):
        lww_map1.update(update)

    assert lww_map1.checksum() == lww_map2.checksum()

    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map1.clock.uuid
    for update in lww_map1.history(until_time_stamp=0):
        lww_map2.update(update)
    assert lww_map1.checksum() != lww_map2.checksum()

    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map1.clock.uuid
    for update in lww_map1.history(from_time_stamp=99):
        lww_map2.update(update)
    assert lww_map1.checksum() != lww_map2.checksum()


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
