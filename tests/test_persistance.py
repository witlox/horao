from horao.conceptual.crdt import LastWriterWinsMap
from horao.conceptual.support import LogicalClock
from horao.logical.infrastructure import LogicalInfrastructure
from horao.persistance.store import Store
from tests.logical.test_scheduler import initialize


async def test_storing_loading_logical_clock():
    clock = LogicalClock()
    store = Store(None)
    await store.save("clock", clock)
    loaded_clock = store.load("clock")
    assert clock == await loaded_clock


async def test_storing_loading_last_writer_wins_map():
    lww_map = LastWriterWinsMap()
    name = "foo"
    value = "bar"
    lww_map.set(name, value, 1)
    store = Store(None)
    await store.save("lww_map", lww_map)
    loaded_lww_map = store.load("lww_map")
    assert lww_map == await loaded_lww_map


async def test_storing_loading_logical_infrastructure():
    dc, dcn = initialize()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    store = Store(None)
    await store.save("infrastructure", infrastructure)
    loaded_infrastructure = await store.load("infrastructure")
    assert infrastructure == loaded_infrastructure
