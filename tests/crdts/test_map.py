from itertools import permutations

from horao.crdts import Update
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
from horao.crdts.map import LastWriterWinsMap, MultiValueMap

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
    "StringClock": StringClock,
}


def test_lww_map_read_after_extend_is_correct():
    lww_map = LastWriterWinsMap()
    view1 = lww_map.read(inject=inject)
    name = String("foo")
    value = String("bar")
    lww_map.set(name, value, 1)
    view2 = lww_map.read(inject=inject)
    assert view1 != view2
    assert name in view2
    assert view2[name] == value


def test_lww_map_read_after_unset_is_correct():
    lww_map = LastWriterWinsMap()
    name = String("foo")
    value = String("bar")
    lww_map.set(name, value, 1)
    view1 = lww_map.read(inject=inject)
    lww_map.unset(name, 1)
    view2 = lww_map.read(inject=inject)
    assert name in view1
    assert name not in view2


def test_lww_map_concurrent_writes_bias_to_higher_writer():
    lww_map = LastWriterWinsMap()
    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map.clock.uuid
    name = String("foo")
    value1 = String("bar")
    value2 = String("test")
    update1 = lww_map.set(name, value1, 1)
    update2 = lww_map2.set(name, value2, 3)
    lww_map.update(update2)
    lww_map2.update(update1)

    assert lww_map.checksums() == lww_map2.checksums()
    assert lww_map.read(inject=inject)[name] == value2
    assert lww_map2.read(inject=inject)[name] == value2


def test_lww_map_checksums_change_after_update():
    lww_map = LastWriterWinsMap()
    lww_map.set(String("foo"), String("bar"), 1)
    checksums1 = lww_map.checksums()
    lww_map.set(String("foo"), String("rab"), 1)
    checksums2 = lww_map.checksums()
    lww_map.set(String("oof"), String("rab"), 1)
    checksums3 = lww_map.checksums()

    assert checksums1 != checksums2
    assert checksums1 != checksums3
    assert checksums2 != checksums3


def test_lww_map_update_is_idempotent():
    lww_map = LastWriterWinsMap()
    update = lww_map.set(String("foo"), String("bar"), 1)
    checksums1 = lww_map.checksums()
    view1 = lww_map.read(inject=inject)
    lww_map.update(update)
    checksums2 = lww_map.checksums()
    view2 = lww_map.read(inject=inject)

    assert checksums1 == checksums2
    assert view1 == view2


def test_lww_map_updates_are_commutative():
    lww_map1 = LastWriterWinsMap()
    lww_map2 = LastWriterWinsMap(clock=ScalarClock(uuid=lww_map1.clock.uuid))
    update1 = lww_map1.set(String("foo"), String("bar"), 1)
    update2 = lww_map1.unset(String("foo"), 1)

    lww_map2.update(update2)
    lww_map2.update(update1)

    assert lww_map2.read(inject=inject) == lww_map1.read(inject=inject)


def test_lww_map_updates_from_history_converge():
    lww_map1 = LastWriterWinsMap()
    lww_map2 = LastWriterWinsMap(clock=ScalarClock(0, lww_map1.clock.uuid))
    lww_map1.set(String("foo"), String("bar"), 1)
    lww_map1.set(String("foo"), String("rab"), 1)
    lww_map1.set(String("oof"), String("rab"), 1)

    for update in lww_map1.history():
        lww_map2.update(update)

    assert lww_map1.checksums() == lww_map2.checksums()

    histories = permutations(lww_map1.history())
    for history in histories:
        lww_map2 = LastWriterWinsMap(clock=ScalarClock(0, lww_map1.clock.uuid))
        for update in history:
            lww_map2.update(update)
        assert lww_map2.read(inject=inject) == lww_map1.read(inject=inject)


def test_lww_map_pack_unpack_e2e():
    lww_map = LastWriterWinsMap()
    lww_map.set(String("foo"), String("bar"), 1)
    lww_map.set(String("foo"), String("rab"), 1)
    lww_map.set(String("foof"), String("barb"), 1)
    lww_map.unset(String("foof"), 1)
    lww_map.set(String("oof"), String("rab"), 1)
    packed = lww_map.pack()
    unpacked = LastWriterWinsMap.unpack(packed, inject=inject)

    assert unpacked.checksums() == lww_map.checksums()


def test_lww_map_pack_unpack_e2e_with_injected_clock():
    lww_map = LastWriterWinsMap(clock=StringClock())
    lww_map.set(String("first name"), String("first value"), 1)
    lww_map.set(String("second name"), String("second value"), 1)
    packed = lww_map.pack()

    unpacked = LastWriterWinsMap.unpack(packed, inject=inject)

    assert unpacked.clock == lww_map.clock
    assert unpacked.read(inject=inject) == lww_map.read(inject=inject)


def test_lww_map_convergence_from_ts():
    lww_map1 = LastWriterWinsMap()
    lww_map2 = LastWriterWinsMap()
    lww_map2.clock.uuid = lww_map1.clock.uuid
    for i in range(10):
        update = lww_map1.set(Integer(i), Integer(i), 1)
        lww_map2.update(update)
    assert lww_map1.checksums() == lww_map2.checksums()

    lww_map1.set(Integer(69420), Integer(69420), 1)
    lww_map1.set(Integer(42096), Integer(42096), 1)
    lww_map2.set(Integer(23878), Integer(23878), 2)

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

    # prove it does not converge from bad ts parameters
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


def test_lww_map_merkle_history_e2e():
    lww_map1 = LastWriterWinsMap()
    lww_map2 = LastWriterWinsMap(clock=ScalarClock(0, lww_map1.clock.uuid))
    lww_map2.update(
        lww_map1.set(
            "hello world",
            1,
            b"1",
        )
    )
    lww_map2.update(
        lww_map1.set(
            b"hello world",
            2,
            b"1",
        )
    )
    lww_map1.unset("hello world", 1)
    lww_map1.set(
        "hello",
        420,
        b"1",
    )
    lww_map2.set(
        "hello",
        b"world",
        b"2",
    )

    history1 = lww_map1.get_merkle_history()
    history2 = lww_map2.get_merkle_history()
    cidmap1 = history1[2]
    cidmap2 = history2[2]

    diff1 = lww_map1.resolve_merkle_histories(history2)
    diff2 = lww_map2.resolve_merkle_histories(history1)
    assert len(diff1) == 2, [d.hex() for d in diff1]
    assert len(diff2) == 2, [d.hex() for d in diff2]

    for cid in diff1:
        update = cidmap2[cid]
        lww_map1.update(Update.unpack(update, inject=inject))
    for cid in diff2:
        update = cidmap1[cid]
        lww_map2.update(Update.unpack(update, inject=inject))

    assert lww_map1.checksums() == lww_map2.checksums()
    assert lww_map1.get_merkle_history() == lww_map2.get_merkle_history()


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


def test_mv_map_read_after_extend_is_correct():
    mv_map = MultiValueMap()
    view1 = mv_map.read(inject=inject)
    name = String("foo")
    value = String("bar")
    mv_map.set(name, value)
    view2 = mv_map.read(inject=inject)
    assert view1 != view2
    assert name in view2
    assert view2[name] == (value,)


def test_mv_map_read_after_unset_is_correct():
    mv_map = MultiValueMap()
    name = String("foo")
    value = String("bar")
    mv_map.set(name, value)
    view1 = mv_map.read(inject=inject)
    mv_map.unset(name)
    view2 = mv_map.read(inject=inject)
    assert name in view1
    assert name not in view2


def test_mv_map_concurrent_writes_preserve_all_values():
    mv_map = MultiValueMap()
    mv_map2 = MultiValueMap()
    mv_map2.clock.uuid = mv_map.clock.uuid
    name = String("foo")
    value1 = String("bar")
    value2 = String("test")
    update1 = mv_map.set(name, value1)
    update2 = mv_map2.set(name, value2)
    mv_map.update(update2)
    mv_map2.update(update1)

    assert mv_map.read(inject=inject)[name] == (value1, value2)
    assert mv_map.checksums() == mv_map2.checksums()


def test_mv_map_checksums_change_after_update():
    mv_map = MultiValueMap()
    mv_map.set(String("foo"), String("bar"))
    checksums1 = mv_map.checksums()
    mv_map.set(String("foo"), String("bruf"))
    checksums2 = mv_map.checksums()
    mv_map.set(String("oof"), String("bruf"))
    checksums3 = mv_map.checksums()

    assert checksums1 != checksums2
    assert checksums1 != checksums3
    assert checksums2 != checksums3


def test_mv_map_update_is_idempotent():
    mv_map = MultiValueMap()
    update = mv_map.set(String("foo"), String("bar"))
    checksums1 = mv_map.checksums()
    view1 = mv_map.read(inject=inject)
    mv_map.update(update)
    checksums2 = mv_map.checksums()
    view2 = mv_map.read(inject=inject)

    assert checksums1 == checksums2
    assert view1 == view2


def test_mv_map_updates_are_commutative():
    mv_map1 = MultiValueMap()
    mv_map2 = MultiValueMap(clock=ScalarClock(uuid=mv_map1.clock.uuid))
    update1 = mv_map1.set(String("foo"), String("bar"))
    update2 = mv_map1.unset(String("foo"))

    mv_map2.update(update2)
    mv_map2.update(update1)

    assert mv_map2.read() == mv_map1.read()


def test_mv_map_updates_from_history_converge():
    mv_map1 = MultiValueMap()
    mv_map2 = MultiValueMap(clock=ScalarClock(0, mv_map1.clock.uuid))
    mv_map1.set(String("foo"), String("bar"))
    mv_map1.set(String("foo"), String("bruf"))
    mv_map1.set(String("oof"), String("bruf"))

    for update in mv_map1.history():
        mv_map2.update(update)

    assert mv_map1.checksums() == mv_map2.checksums()

    histories = permutations(mv_map1.history())
    for history in histories:
        mv_map2 = MultiValueMap(clock=ScalarClock(0, mv_map1.clock.uuid))
        for update in history:
            mv_map2.update(update)
        assert mv_map2.read(inject=inject) == mv_map1.read(inject=inject)


def test_mv_map_pack_unpack_e2e():
    mv_map = MultiValueMap()
    mv_map.set(String("foo"), String("bar"))
    mv_map.set(String("foo"), String("bruf"))
    mv_map.set(String("floof"), String("bruf"))
    mv_map.unset(String("floof"))
    mv_map.set(String("oof"), String("bruf"))
    packed = mv_map.pack()
    unpacked = MultiValueMap.unpack(packed, inject=inject)

    assert unpacked.checksums() == mv_map.checksums()


def test_mv_map_pack_unpack_e2e_with_injected_clock():
    mvm = MultiValueMap(clock=StringClock())
    mvm.set(
        String("first name"),
        String("first value"),
    )
    mvm.set(
        String("second name"),
        String("second value"),
    )
    packed = mvm.pack()

    unpacked = MultiValueMap.unpack(packed, inject=inject)

    assert unpacked.clock == mvm.clock
    assert unpacked.read(inject=inject) == mvm.read(inject=inject)


def test_mv_map_convergence_from_ts():
    mv_map1 = MultiValueMap()
    mv_map2 = MultiValueMap()
    mv_map2.clock.uuid = mv_map1.clock.uuid
    for i in range(10):
        update = mv_map1.set(
            Integer(i),
            Integer(i),
        )
        mv_map2.update(update)
    assert mv_map1.checksums() == mv_map2.checksums()

    mv_map1.set(Integer(69420), Integer(69420))
    mv_map1.set(Integer(42096), Integer(42096))
    mv_map2.set(Integer(23878), Integer(23878))

    from_ts = 0
    until_ts = mv_map1.clock.read()
    chksm1 = mv_map1.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
    chksm2 = mv_map2.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
    while chksm1 != chksm2 and until_ts > 0:
        until_ts -= 1
        chksm1 = mv_map1.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
        chksm2 = mv_map2.checksums(from_time_stamp=from_ts, until_time_stamp=until_ts)
    from_ts = until_ts
    assert from_ts > 0

    for update in mv_map1.history(from_time_stamp=from_ts):
        mv_map2.update(update)
    for update in mv_map2.history(from_time_stamp=from_ts):
        mv_map1.update(update)

    assert mv_map1.checksums() == mv_map2.checksums()

    mv_map2 = MultiValueMap()
    mv_map2.clock.uuid = mv_map1.clock.uuid
    for update in mv_map1.history(until_time_stamp=0):
        mv_map2.update(update)
    assert mv_map1.checksums() != mv_map2.checksums()

    mv_map2 = MultiValueMap()
    mv_map2.clock.uuid = mv_map1.clock.uuid
    for update in mv_map1.history(from_time_stamp=99):
        mv_map2.update(update)
    assert mv_map1.checksums() != mv_map2.checksums()


def test_mv_map_merkle_history_e2e():
    mvm1 = MultiValueMap()
    mvm2 = MultiValueMap(clock=ScalarClock(0, mvm1.clock.uuid))
    mvm2.update(
        mvm1.set(
            String("hello world"),
            Integer(1),
        )
    )
    mvm2.update(
        mvm1.set(
            Bytes(b"hello world"),
            Integer(2),
        )
    )
    mvm1.unset(String("hello world"))
    mvm1.set(
        String("not the lipsum"),
        Integer(420),
    )
    mvm2.set(
        String("not the lipsum"),
        Bytes(b"yellow submarine"),
    )

    history1 = mvm1.get_merkle_history()
    history2 = mvm2.get_merkle_history()

    cidmap1 = history1[2]
    cidmap2 = history2[2]

    diff1 = mvm1.resolve_merkle_histories(history2)
    diff2 = mvm2.resolve_merkle_histories(history1)
    assert len(diff1) == 2, [d.hex() for d in diff1]
    assert len(diff2) == 2, [d.hex() for d in diff2]

    for cid in diff1:
        mvm1.update(Update.unpack(cidmap2[cid], inject=inject))
    for cid in diff2:
        mvm2.update(Update.unpack(cidmap1[cid], inject=inject))

    assert mvm1.checksums() == mvm2.checksums()
    assert mvm1.get_merkle_history() == mvm2.get_merkle_history()


def test_mv_map_event_listeners_e2e():
    mvm = MultiValueMap()
    logs = []

    def add_log(update: Update):
        logs.append(update)

    assert len(logs) == 0
    mvm.set("name", "value")
    assert len(logs) == 0
    mvm.add_listener(add_log)
    mvm.set("name", "value")
    assert len(logs) == 1
    mvm.remove_listener(add_log)
    mvm.set("name", "value")
    assert len(logs) == 1
