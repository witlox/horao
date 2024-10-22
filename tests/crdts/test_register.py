import packify

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
from horao.crdts.protocols import CRDT
from horao.crdts.register import LastWriterWinsRegister, MultiValueRegister

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


def test_lww_register_read_returns_value():
    lww_register = LastWriterWinsRegister(String("test"), String("foobar"))
    assert lww_register.read(inject=inject).value == "foobar"
    lww_register = LastWriterWinsRegister("test", "foobar")
    assert lww_register.read() == "foobar"


def test_lww_register_write_returns_state_update_and_sets_value():
    lww_register = LastWriterWinsRegister(Bytes(b"test"), Bytes(b"foobar"))
    lww_register.write(Bytes(b"barfoo"), 1, inject=inject)
    assert lww_register.read(inject=inject).value == b"barfoo"


def test_lww_register_history_returns_tuple_of_state_update():
    lww_register = LastWriterWinsRegister(String("test"), String("foobar"))
    lww_register.write(String("sdsd"), b"2")
    lww_register.write(String("barfoo"), b"1")
    history = lww_register.history()
    assert history is not None


def test_lww_register_concurrent_writes_bias_to_higher_writer():
    lww_register1 = LastWriterWinsRegister(String("test"))
    clock = ScalarClock.unpack(lww_register1.clock.pack())
    lww_register2 = LastWriterWinsRegister(String("test"), clock=clock)

    update1 = lww_register1.write(String("foobar"), b"1")
    update2 = lww_register2.write(String("barfoo"), b"2")
    lww_register1.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read(inject=inject) == lww_register2.read(inject=inject)
    assert lww_register1.read(inject=inject).value == "barfoo"


def test_lww_register_concurrent_writes_bias_to_one_value():
    lww_register1 = LastWriterWinsRegister(String("test"))
    clock = ScalarClock.unpack(lww_register1.clock.pack())
    lww_register2 = LastWriterWinsRegister(String("test"), clock=clock)

    update1 = lww_register1.write(String("foobar"), [b"1", 2, "3"])
    update2 = lww_register2.write(String("barfoo"), [b"1", 2, "2"])
    lww_register1.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read(inject=inject) == lww_register2.read(inject=inject)
    assert lww_register1.read(inject=inject).value == "foobar"


def test_lww_register_checksums_returns_tuple_of_int():
    lww_register = LastWriterWinsRegister(String("test"), String("thing"))
    assert lww_register.checksums() is not None


def test_lww_register_checksums_change_after_update():
    lww_register1 = LastWriterWinsRegister(String("test"), String(""))
    clock = ScalarClock.unpack(lww_register1.clock.pack())
    lww_register2 = LastWriterWinsRegister(String("test"), String(""), clock=clock)
    checksums1 = lww_register1.checksums()

    assert lww_register2.checksums() == checksums1

    lww_register1.write(String("foo"), b"1")
    lww_register2.write(String("bar"), b"2")

    assert lww_register1.checksums() != checksums1
    assert lww_register2.checksums() != checksums1
    assert lww_register1.checksums() != lww_register2.checksums()


def test_lww_register_update_is_idempotent():
    lww_register1 = LastWriterWinsRegister(String("test"))
    clock1 = ScalarClock.unpack(lww_register1.clock.pack())
    lww_register2 = LastWriterWinsRegister(String("test"), clock=clock1)

    update = lww_register1.write(String("foo"), b"1")
    view1 = lww_register1.read(inject=inject)
    lww_register1.update(update)
    assert lww_register1.read(inject=inject) == view1
    lww_register2.update(update)
    view2 = lww_register2.read(inject=inject)
    lww_register2.update(update)
    assert lww_register2.read(inject=inject) == view2

    update = lww_register2.write(String("bar"), b"2")
    lww_register1.update(update)
    view1 = lww_register1.read(inject=inject)
    lww_register1.update(update)
    assert lww_register1.read(inject=inject) == view1
    lww_register2.update(update)
    view2 = lww_register2.read(inject=inject)
    lww_register2.update(update)
    assert lww_register2.read(inject=inject) == view2


def test_lww_register_updates_are_commutative():
    lww_register1 = LastWriterWinsRegister(String("test"))
    clock1 = ScalarClock(uuid=lww_register1.clock.uuid)
    lww_register2 = LastWriterWinsRegister(String("test"), clock=clock1)

    update1 = lww_register1.write(String("foo1"), b"1")
    update2 = lww_register1.write(String("foo2"), b"1")
    lww_register2.update(update2)
    lww_register2.update(update1)

    assert lww_register1.read(inject=inject) == lww_register2.read(inject=inject)


def test_lww_register_update_from_history_converges():
    lww_register1 = LastWriterWinsRegister(String("test"))
    clock1 = ScalarClock.unpack(lww_register1.clock.pack())
    clock2 = ScalarClock.unpack(lww_register1.clock.pack())
    lww_register2 = LastWriterWinsRegister(String("test"), clock=clock1)
    lww_register3 = LastWriterWinsRegister(String("test"), clock=clock2)

    update = lww_register1.write(String("foo1"), b"1")
    lww_register2.update(update)
    lww_register2.write(String("bar"), b"2")

    for item in lww_register2.history():
        lww_register1.update(item)
        lww_register3.update(item)

    assert (
        lww_register1.read(inject=inject).value
        == lww_register2.read(inject=inject).value
    )
    assert (
        lww_register1.read(inject=inject).value
        == lww_register3.read(inject=inject).value
    )
    assert lww_register1.checksums() == lww_register2.checksums()
    assert lww_register1.checksums() == lww_register3.checksums()


def test_lww_register_pack_unpack_e2e():
    lww_register = LastWriterWinsRegister(String("test"), String(""))
    packed = lww_register.pack()
    unpacked = LastWriterWinsRegister.unpack(packed, inject=inject)

    assert unpacked.clock == lww_register.clock
    assert unpacked.read(inject=inject) == lww_register.read(inject=inject)


def test_lww_register_pack_unpack_e2e_with_injected_clock():
    lww_register = LastWriterWinsRegister(
        name=String("test register"), clock=StringClock()
    )
    lww_register.write(String("first"), b"1")
    lww_register.write(String("second"), b"1")
    packed = lww_register.pack()

    unpacked = LastWriterWinsRegister.unpack(packed, inject=inject)

    assert unpacked.clock == lww_register.clock
    assert unpacked.read(inject=inject) == lww_register.read(inject=inject)


def test_lww_register_history_return_value_determined_by_from_ts_and_until_ts():
    lww_register = LastWriterWinsRegister(name=String("test register"))
    lww_register.write(String("first"), 1)
    lww_register.write(String("second"), 1)

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
    mv_register = MultiValueRegister(String("test"), [String("foobar")])
    assert len(mv_register.read(inject=inject)) == 1
    assert mv_register.read(inject=inject)[0].value == "foobar"

    mv_register = MultiValueRegister("test", ["foobar"])
    assert len(mv_register.read(inject=inject)) == 1
    assert mv_register.read(inject=inject)[0] == "foobar"


def test_mv_register_write_returns_state_update_and_sets_values():
    mv_register = MultiValueRegister(String("test"), [Float("0.123")])
    mv_register.write(Bytes(b"barfoo"))
    assert list(mv_register.read(inject=inject))[0].value == b"barfoo"


def test_mv_register_history_returns_tuple_of_state_update():
    mv_register = MultiValueRegister(String("test"), [String("foobar")])
    mv_register.write(String("sdsd"))
    mv_register.write(String("barfoo"))
    history = mv_register.history()
    assert history is not None


def test_mv_register_concurrent_writes_retain_all_values():
    mv_register1 = MultiValueRegister(String("test"))
    mv_register2 = MultiValueRegister(String("test"))
    mv_register2.clock.uuid = mv_register1.clock.uuid

    update1 = mv_register1.write(String("foobar"))
    update2 = mv_register2.write(String("barfoo"))
    mv_register1.update(update2)
    mv_register2.update(update1)
    expected = (String("barfoo"), String("foobar"))

    assert mv_register1.read(inject=inject) == mv_register2.read(inject=inject)
    assert mv_register1.read(inject=inject) == expected


def test_mv_register_checksums_returns_tuple_of_int():
    mv_register = MultiValueRegister(String("test"), [String("foobar")])
    assert mv_register is not None


def test_mv_register_checksums_change_after_update():
    mv_register1 = MultiValueRegister(String("test"), [String("foobar")])
    mv_register2 = MultiValueRegister(String("test"), [String("foobar")])
    mv_register2.clock.uuid = mv_register1.clock.uuid
    checksums1 = mv_register1.checksums()

    assert mv_register2.checksums() == checksums1

    mv_register1.write(String("a"))
    mv_register2.write(String("b"))

    assert mv_register1.checksums() != checksums1
    assert mv_register2.checksums() != checksums1
    assert mv_register1.checksums() != mv_register2.checksums()


def test_mv_register_update_is_idempotent():
    mv_register1 = MultiValueRegister(String("test"))
    mv_register2 = MultiValueRegister(String("test"))
    mv_register2.clock.uuid = mv_register1.clock.uuid

    update = mv_register1.write(String("foo"))
    view1 = mv_register1.read(inject=inject)
    mv_register1.update(update)
    assert mv_register1.read(inject=inject) == view1
    mv_register2.update(update)
    view2 = mv_register2.read(inject=inject)
    mv_register2.update(update)
    assert mv_register2.read(inject=inject) == view2

    update = mv_register2.write(String("bar"))
    mv_register1.update(update)
    view1 = mv_register1.read(inject=inject)
    mv_register1.update(update)
    assert mv_register1.read(inject=inject) == view1
    mv_register2.update(update)
    view2 = mv_register2.read(inject=inject)
    mv_register2.update(update)
    assert mv_register2.read(inject=inject) == view2


def test_mv_register_updates_are_commutative():
    mv_register1 = MultiValueRegister(String("test"))
    mv_register2 = MultiValueRegister(String("test"))
    mv_register2.clock.uuid = mv_register1.clock.uuid

    update1 = mv_register1.write(String("foo"))
    update2 = mv_register1.write(String("bar"))
    mv_register2.update(update2)
    mv_register2.update(update1)

    assert mv_register1.read(inject=inject) == mv_register2.read(inject=inject)


def test_mv_register_update_from_history_converges():
    mv_register1 = MultiValueRegister(String("test"))
    mv_register2 = MultiValueRegister(String("test"))
    mv_register2.clock.uuid = mv_register1.clock.uuid
    mv_register3 = MultiValueRegister(String("test"))
    mv_register3.clock.uuid = mv_register1.clock.uuid

    update = mv_register1.write(String("foo"))
    mv_register2.update(update)
    mv_register2.write(String("bar"))

    for item in mv_register2.history():
        mv_register1.update(item)
        mv_register3.update(item)

    assert mv_register1.read(inject=inject) == mv_register2.read(inject=inject)
    assert mv_register1.read(inject=inject) == mv_register3.read(inject=inject)
    assert mv_register1.checksums() == mv_register2.checksums()
    assert mv_register1.checksums() == mv_register3.checksums()


def test_mv_register_pack_unpack_e2e():
    mv_register = MultiValueRegister(String("test"), [String("foobar")])

    packed = mv_register.pack()
    unpacked = MultiValueRegister.unpack(packed, inject=inject)

    assert isinstance(unpacked, MultiValueRegister)
    assert unpacked.clock == mv_register.clock
    assert unpacked.read(inject=inject) == mv_register.read(inject=inject)


def test_mv_register_pack_unpack_e2e_with_injected_clock():
    mv_register = MultiValueRegister(name=String("test register"), clock=StringClock())
    mv_register.write(String("first"))
    mv_register.write(String("second"))
    packed = mv_register.pack()

    unpacked = MultiValueRegister.unpack(packed, inject=inject)

    assert unpacked.clock == mv_register.clock
    assert unpacked.read(inject=inject) == mv_register.read(inject=inject)


def test_mv_register_history_return_value_determined_by_from_ts_and_until_ts():
    mv_register = MultiValueRegister(name=String("test register"))
    mv_register.write(String("first"))
    mv_register.write(String("second"))

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
