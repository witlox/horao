import pytest

from horao.conceptual.crdt import LastWriterWinsMap, LastWriterWinsRegister
from horao.conceptual.support import LogicalClock
from horao.logical.infrastructure import LogicalInfrastructure
from horao.persistance.store import Store
from tests.logical.test_scheduler import initialize_logical_infrastructure

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_storing_loading_logical_clock():
    clock = LogicalClock()
    store = Store(None)
    await store.save("clock", clock)
    loaded_clock = await store.load("clock")
    assert clock == loaded_clock


@pytest.mark.asyncio
async def test_storing_loading_observed_removed_set():
    observed_removed_set = set()
    observed_removed_set.add("foo")
    observed_removed_set.add("bar")
    store = Store(None)
    await store.save("observed_removed_set", observed_removed_set)
    loaded_observed_removed_set = await store.load("observed_removed_set")
    assert observed_removed_set == loaded_observed_removed_set


@pytest.mark.asyncio
async def test_storing_loading_last_writer_wins_register():
    lww_register = LastWriterWinsRegister("test", "foo")
    update = lww_register.write("foobar", 1)
    lww_register.update(update)

    store = Store(None)
    await store.save("lww_register", lww_register)
    loaded_lww_register = await store.load("lww_register")
    assert lww_register == loaded_lww_register


@pytest.mark.asyncio
async def test_storing_loading_last_writer_wins_map():
    lww_map = LastWriterWinsMap()
    name = "foo"
    value = "bar"
    lww_map.set(name, value, 1)
    store = Store(None)
    await store.save("lww_map", lww_map)
    loaded_lww_map = await store.load("lww_map")
    assert lww_map == loaded_lww_map


@pytest.mark.asyncio
async def test_storing_loading_logical_infrastructure():
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    store = Store(None)
    await store.save("infrastructure", infrastructure)
    loaded_infrastructure = await store.load("infrastructure")
    assert infrastructure == loaded_infrastructure
