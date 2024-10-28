from horao.models.internal import LogicalClock, Update


def test_scalar_clock_read_changes_only_after_update():
    clock = LogicalClock()
    t0 = clock.read()
    assert t0 == clock.read()
    clock.update()
    assert clock.read() > t0


def test_scalar_clock_is_later_returns_correct_bools():
    assert type(LogicalClock.is_later(1, 0)) is bool
    assert LogicalClock.is_later(1, 0)
    assert not LogicalClock.is_later(0, 0)
    assert not LogicalClock.is_later(0, 1)


def test_scalar_clock_are_concurrent_returns_correct_bools():
    assert type(LogicalClock.are_concurrent(0, 0)) is bool
    assert LogicalClock.are_concurrent(0, 0)
    assert not LogicalClock.are_concurrent(1, 0)
    assert not LogicalClock.are_concurrent(1, 2)


def test_scalar_clock_compare_returns_correct_int():
    assert type(LogicalClock.compare(0, 0)) is int
    assert LogicalClock.compare(0, 0) == 0
    assert LogicalClock.compare(1, 0) == 1
    assert LogicalClock.compare(1, 2) == -1
