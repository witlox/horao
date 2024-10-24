from itertools import permutations

from horao.models.crdt import (
    LastWriterWinsRegister,
    MultiValueRegister,
    ObservedRemovedSet,
    LastWriterWinsMap,
)
from horao.models.internal import ScalarClock, Update


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
    clock = ScalarClock.unpack(lww_register1.clock.pack())
    lww_register2 = LastWriterWinsRegister("test", clock=clock)

    update1 = lww_register1.write("foobar", b"1")
    update2 = lww_register2.write("barfoo", b"2")
    lww_register1.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read() == lww_register2.read()
    assert lww_register1.read() == "barfoo"


def test_lww_register_concurrent_writes_bias_to_one_value():
    lww_register1 = LastWriterWinsRegister("test")
    clock = ScalarClock.unpack(lww_register1.clock.pack())
    lww_register2 = LastWriterWinsRegister("test", clock=clock)

    update1 = lww_register1.write("foobar", [b"1", 2, "3"])
    update2 = lww_register2.write("barfoo", [b"1", 2, "2"])
    lww_register1.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read() == lww_register2.read()
    assert lww_register1.read() == "foobar"


def test_lww_register_checksums_returns_tuple_of_int():
    lww_register = LastWriterWinsRegister("test", "thing")
    assert lww_register.checksums() is not None


def test_lww_register_checksums_change_after_update():
    lww_register1 = LastWriterWinsRegister("test", "")
    clock = ScalarClock.unpack(lww_register1.clock.pack())
    lww_register2 = LastWriterWinsRegister("test", "", clock=clock)
    checksums1 = lww_register1.checksums()

    assert lww_register2.checksums() == checksums1

    lww_register1.write("foo", b"1")
    lww_register2.write("bar", b"2")

    assert lww_register1.checksums() != checksums1
    assert lww_register2.checksums() != checksums1
    assert lww_register1.checksums() != lww_register2.checksums()


def test_lww_register_update_is_idempotent():
    lww_register1 = LastWriterWinsRegister("test")
    clock1 = ScalarClock.unpack(lww_register1.clock.pack())
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
    clock1 = ScalarClock(uuid=lww_register1.clock.uuid)
    lww_register2 = LastWriterWinsRegister("test", clock=clock1)

    update1 = lww_register1.write("foo1", b"1")
    update2 = lww_register1.write("foo2", b"1")
    lww_register2.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read() == lww_register2.read()


def test_lww_register_update_from_history_converges():
    lww_register1 = LastWriterWinsRegister("test")
    clock1 = ScalarClock.unpack(lww_register1.clock.pack())
    clock2 = ScalarClock.unpack(lww_register1.clock.pack())
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
    assert lww_register1.checksums() == lww_register2.checksums()
    assert lww_register1.checksums() == lww_register3.checksums()


def test_lww_register_pack_unpack_e2e():
    lww_register = LastWriterWinsRegister("test", "")
    packed = lww_register.pack()
    unpacked = LastWriterWinsRegister.unpack(packed)

    assert unpacked.clock == lww_register.clock
    assert unpacked.read() == lww_register.read()


def test_lww_register_history_return_value_determined_by_from_ts_and_until_ts():
    lww_register = LastWriterWinsRegister(name="test register")
    lww_register.write("first", 1)
    lww_register.write("second", 1)

    assert len(lww_register.history(from_time_stamp=99)) == 0
    assert len(lww_register.history(until_time_stamp=0)) == 0
    assert len(lww_register.history(from_time_stamp=0, until_time_stamp=99)) == 1


def test_lww_register_merkle_history_e2e():
    lww_register1 = LastWriterWinsRegister("test")
    lww_register2 = LastWriterWinsRegister(
        "test", clock=ScalarClock(0, lww_register1.clock.uuid)
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

    assert lww_register1.checksums() == lww_register2.checksums()


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


def test_mv_register_read_returns_set_of_values():
    mv_register = MultiValueRegister("test", ["foobar"])
    assert len(mv_register.read()) == 1
    assert mv_register.read()[0] == "foobar"

    mv_register = MultiValueRegister("test", ["foobar"])
    assert len(mv_register.read()) == 1
    assert mv_register.read()[0] == "foobar"


def test_mv_register_write_returns_state_update_and_sets_values():
    mv_register = MultiValueRegister("test", [0.123])
    mv_register.write(b"barfoo")
    assert list(mv_register.read())[0] == b"barfoo"


def test_mv_register_history_returns_tuple_of_state_update():
    mv_register = MultiValueRegister("test", ["foobar"])
    mv_register.write("sdsd")
    mv_register.write("barfoo")
    history = mv_register.history()
    assert history is not None


def test_mv_register_concurrent_writes_retain_all_values():
    mv_register1 = MultiValueRegister("test")
    mv_register2 = MultiValueRegister("test")
    mv_register2.clock.uuid = mv_register1.clock.uuid

    update1 = mv_register1.write("foobar")
    update2 = mv_register2.write("barfoo")
    mv_register1.update(update2)
    mv_register2.update(update1)
    expected = ("barfoo", "foobar")

    assert mv_register1.read() == mv_register2.read()
    assert mv_register1.read() == expected


def test_mv_register_checksums_returns_tuple_of_int():
    mv_register = MultiValueRegister("test", ["foobar"])
    assert mv_register is not None


def test_mv_register_checksums_change_after_update():
    mv_register1 = MultiValueRegister("test", ["foobar"])
    mv_register2 = MultiValueRegister("test", ["foobar"])
    mv_register2.clock.uuid = mv_register1.clock.uuid
    checksums1 = mv_register1.checksums()

    assert mv_register2.checksums() == checksums1

    mv_register1.write("a")
    mv_register2.write("b")

    assert mv_register1.checksums() != checksums1
    assert mv_register2.checksums() != checksums1
    assert mv_register1.checksums() != mv_register2.checksums()


def test_mv_register_update_is_idempotent():
    mv_register1 = MultiValueRegister("test")
    mv_register2 = MultiValueRegister("test")
    mv_register2.clock.uuid = mv_register1.clock.uuid

    update = mv_register1.write("foo")
    view1 = mv_register1.read()
    mv_register1.update(update)
    assert mv_register1.read() == view1
    mv_register2.update(update)
    view2 = mv_register2.read()
    mv_register2.update(update)
    assert mv_register2.read() == view2

    update = mv_register2.write("bar")
    mv_register1.update(update)
    view1 = mv_register1.read()
    mv_register1.update(update)
    assert mv_register1.read() == view1
    mv_register2.update(update)
    view2 = mv_register2.read()
    mv_register2.update(update)
    assert mv_register2.read() == view2


def test_mv_register_updates_are_commutative():
    mv_register1 = MultiValueRegister("test")
    mv_register2 = MultiValueRegister("test")
    mv_register2.clock.uuid = mv_register1.clock.uuid

    update1 = mv_register1.write("foo")
    update2 = mv_register1.write("bar")
    mv_register2.update(update2)
    mv_register2.update(update1)

    assert mv_register1.read() == mv_register2.read()


def test_mv_register_update_from_history_converges():
    mv_register1 = MultiValueRegister("test")
    mv_register2 = MultiValueRegister("test")
    mv_register2.clock.uuid = mv_register1.clock.uuid
    mv_register3 = MultiValueRegister("test")
    mv_register3.clock.uuid = mv_register1.clock.uuid

    update = mv_register1.write("foo")
    mv_register2.update(update)
    mv_register2.write("bar")

    for item in mv_register2.history():
        mv_register1.update(item)
        mv_register3.update(item)

    assert mv_register1.read() == mv_register2.read()
    assert mv_register1.read() == mv_register3.read()
    assert mv_register1.checksums() == mv_register2.checksums()
    assert mv_register1.checksums() == mv_register3.checksums()


def test_mv_register_pack_unpack_e2e():
    mv_register = MultiValueRegister("test", ["foobar"])

    packed = mv_register.pack()
    unpacked = MultiValueRegister.unpack(packed)

    assert isinstance(unpacked, MultiValueRegister)
    assert unpacked.clock == mv_register.clock
    assert unpacked.read() == mv_register.read()


def test_mv_register_history_return_value_determined_by_from_ts_and_until_ts():
    mv_register = MultiValueRegister(name="test register")
    mv_register.write("first")
    mv_register.write("second")

    assert len(mv_register.history(from_time_stamp=99)) == 0
    assert len(mv_register.history(until_time_stamp=0)) == 0
    assert len(mv_register.history(from_time_stamp=0, until_time_stamp=99)) == 1


def test_mv_register_merkle_history_e2e():
    mv_register1 = MultiValueRegister("test")
    mv_register2 = MultiValueRegister(
        "test", clock=ScalarClock(0, mv_register1.clock.uuid)
    )
    mv_register2.update(mv_register1.write("hello world"))
    mv_register2.update(mv_register1.write(b"hello world"))
    mv_register1.write("hello")
    mv_register2.write(b"world")

    history1 = mv_register1.get_merkle_history()
    history2 = mv_register2.get_merkle_history()
    cidmap1 = history1[2]
    cidmap2 = history2[2]

    diff1 = mv_register1.resolve_merkle_histories(history2)
    diff2 = mv_register2.resolve_merkle_histories(history1)
    assert len(diff1) == 1, [d.hex() for d in diff1]
    assert len(diff2) == 1, [d.hex() for d in diff2]

    for cid in diff1:
        mv_register1.update(Update.unpack(cidmap2[cid]))
    for cid in diff2:
        mv_register2.update(Update.unpack(cidmap1[cid]))

    assert mv_register1.checksums() == mv_register2.checksums()


def test_mv_register_event_listeners_e2e():
    mv_register = MultiValueRegister("test")
    logs = []

    def add_log(update: Update):
        logs.append(update)

    assert len(logs) == 0
    mv_register.write("value")
    assert len(logs) == 0
    mv_register.add_listener(add_log)
    mv_register.write("value")
    assert len(logs) == 1
    mv_register.remove_listener(add_log)
    mv_register.write("value")
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
    checksum = orset.checksums()
    assert type(checksum) is tuple
    for item in checksum:
        assert type(item) is int


def test_or_set_checksums_change_after_update():
    orset = ObservedRemovedSet()
    checksums1 = orset.checksums()
    orset.observe(1)
    checksums2 = orset.checksums()
    orset.remove(1)
    checksums3 = orset.checksums()
    assert checksums1 != checksums2
    assert checksums2 != checksums3
    assert checksums3 != checksums1


def test_or_set_update_is_idempotent():
    orset1 = ObservedRemovedSet()
    orset2 = ObservedRemovedSet(clock=ScalarClock(0, orset1.clock.uuid))
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
    orset2 = ObservedRemovedSet(clock=ScalarClock(0, orset1.clock.uuid))
    orset1.observe(1)
    orset1.remove(2)
    orset1.observe(3)

    for update in orset1.history():
        orset2.update(update)

    assert orset1.read() == orset2.read()
    assert orset1.checksums() == orset2.checksums()

    histories = permutations(orset1.history())
    for history in histories:
        orset2 = ObservedRemovedSet(clock=ScalarClock(0, orset1.clock.uuid))
        for update in history:
            orset2.update(update)
        assert orset2.read() == orset1.read()
        assert orset2.checksums() == orset1.checksums()


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
    assert orset1.checksums() == orset2.checksums()
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
    assert orset1.checksums() == orset2.checksums()
    for i in range(5):
        update = orset2.remove(i)
        orset1.update(update)
    assert orset1.checksums() == orset2.checksums()

    orset1.observe(69420)
    orset1.observe(42096)
    orset2.observe(23878)

    # not the most efficient algorithm, but it demonstrates the concept
    from_ts = 0
    until_ts = orset1.clock.read()
    while (
        orset1.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
        != orset2.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
        and until_ts > 0
    ):
        until_ts -= 1
    from_ts = until_ts
    assert from_ts > 0

    for update in orset1.history(from_time_stamp=from_ts):
        orset2.update(update)
    for update in orset2.history(from_time_stamp=from_ts):
        orset1.update(update)

    assert orset1.checksums() == orset2.checksums()

    orset2 = ObservedRemovedSet()
    orset2.clock.uuid = orset1.clock.uuid
    for update in orset1.history(until_time_stamp=0):
        orset2.update(update)
    assert orset1.checksums() != orset2.checksums()

    orset2 = ObservedRemovedSet()
    orset2.clock.uuid = orset1.clock.uuid
    for update in orset1.history(from_time_stamp=99):
        orset2.update(update)
    assert orset1.checksums() != orset2.checksums()


def test_or_set_merkle_history_e2e():
    ors1 = ObservedRemovedSet()
    ors2 = ObservedRemovedSet(clock=ScalarClock(0, ors1.clock.uuid))
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
    assert ors1.checksums() == ors2.checksums()


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

    assert lww_map.checksums() == lww_map2.checksums()
    assert lww_map.read()[name] == value2
    assert lww_map2.read()[name] == value2


def test_lww_map_checksums_change_after_update():
    lww_map = LastWriterWinsMap()
    lww_map.set("foo", "bar", 1)
    checksums1 = lww_map.checksums()
    lww_map.set("foo", "rab", 1)
    checksums2 = lww_map.checksums()
    lww_map.set("oof", "rab", 1)
    checksums3 = lww_map.checksums()

    assert checksums1 != checksums2
    assert checksums1 != checksums3
    assert checksums2 != checksums3


def test_lww_map_update_is_idempotent():
    lww_map = LastWriterWinsMap()
    update = lww_map.set("foo", "bar", 1)
    checksums1 = lww_map.checksums()
    view1 = lww_map.read()
    lww_map.update(update)
    checksums2 = lww_map.checksums()
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

    assert unpacked.checksums() == lww_map.checksums()


def test_lww_map_convergence_from_ts():
    lww_map1 = LastWriterWinsMap()
    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map1.clock.uuid
    for i in range(10):
        update = lww_map1.set(i, i, 1)
        lww_map2.update(update)
    assert lww_map1.checksums() == lww_map2.checksums()

    lww_map1.set(69420, 69420, 1)
    lww_map1.set(42096, 42096, 1)
    lww_map2.set(23878, 23878, 2)

    # not the most efficient algorithm, but it demonstrates the concept
    from_ts = 0
    until_ts = lww_map1.clock.read()
    chksm1 = lww_map1.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
    chksm2 = lww_map2.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
    while chksm1 != chksm2 and until_ts > 0:
        until_ts -= 1
        chksm1 = lww_map1.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
        chksm2 = lww_map2.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
    from_ts = until_ts
    assert from_ts > 0

    for update in lww_map1.history(from_time_stamp=from_ts):
        lww_map2.update(update)
    for update in lww_map2.history(from_time_stamp=from_ts):
        lww_map1.update(update)

    assert lww_map1.checksums() == lww_map2.checksums()

    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map1.clock.uuid
    for update in lww_map1.history(until_time_stamp=0):
        lww_map2.update(update)
    assert lww_map1.checksums() != lww_map2.checksums()

    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map1.clock.uuid
    for update in lww_map1.history(from_time_stamp=99):
        lww_map2.update(update)
    assert lww_map1.checksums() != lww_map2.checksums()


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
