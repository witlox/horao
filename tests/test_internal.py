from horao.models.internal import ScalarClock, Update


def test_scalar_clock_instance_has_counter_and_uuid():
    clock = ScalarClock()
    assert hasattr(clock, "counter")
    assert hasattr(clock, "uuid")


def test_scalar_clock_read_returns_int():
    clock = ScalarClock()
    assert type(clock.read()) is int


def test_scalar_clock_read_changes_only_after_update():
    clock = ScalarClock()
    t0 = clock.read()
    assert t0 == clock.read()
    clock.update(t0)
    assert clock.read() > t0


def test_scalar_clock_is_later_returns_correct_bools():
    assert type(ScalarClock.is_later(1, 0)) is bool
    assert ScalarClock.is_later(1, 0)
    assert not ScalarClock.is_later(0, 0)
    assert not ScalarClock.is_later(0, 1)


def test_scalar_clock_are_concurrent_returns_correct_bools():
    assert type(ScalarClock.are_concurrent(0, 0)) is bool
    assert ScalarClock.are_concurrent(0, 0)
    assert not ScalarClock.are_concurrent(1, 0)
    assert not ScalarClock.are_concurrent(1, 2)


def test_scalar_clock_compare_returns_correct_int():
    assert type(ScalarClock.compare(0, 0)) is int
    assert ScalarClock.compare(0, 0) == 0
    assert ScalarClock.compare(1, 0) == 1
    assert ScalarClock.compare(1, 2) == -1


def test_scalar_clock_pack_returns_bytes():
    clock = ScalarClock()
    assert type(clock.pack()) is bytes


def test_scalar_clock_unpack_returns_same_clock():
    clock = ScalarClock()
    clock2 = ScalarClock.unpack(clock.pack())
    assert clock == clock2
    assert clock.uuid == clock2.uuid
    assert clock.counter == clock2.counter


def test_state_is_dataclass_with_attributes():
    update = Update(b"123", 123, 321)
    assert isinstance(update, Update)


def test_state_pack_returns_bytes():
    update = Update(b"123", 123, 321)
    assert type(update.pack()) is bytes


def test_state_unpack_returns_state_update():
    data = bytes.fromhex(
        "6c0000001a620000000331323369000000040000007b690000000400000141"
    )
    update = Update.unpack(data)
    assert isinstance(update, Update)


def test_state_pack_unpack_e2e():
    update = Update(b"uuid", 123, ("o", (321, "123")))
    packed = update.pack()
    unpacked = Update.unpack(packed)
    assert unpacked == update

    update = Update(b"uuid", 123, (1, b"example"))
    packed = update.pack()
    unpacked = Update.unpack(packed)
    assert unpacked == update

    update = Update(b"uuid", 123, ("o", "name", 1, b"value"))
    packed = update.pack()
    unpacked = Update.unpack(packed)
    assert unpacked == update

    update = Update(b"uuid", 123, ("o", 3, 1, 0.253))
    packed = update.pack()
    unpacked = Update.unpack(packed)
    assert unpacked == update
