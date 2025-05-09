import json

import pytest

from horao.conceptual.crdt import LastWriterWinsMap, LastWriterWinsRegister
from horao.conceptual.osi_layers import LinkLayer
from horao.conceptual.support import LogicalClock
from horao.logical.infrastructure import LogicalInfrastructure
from horao.persistance import HoraoDecoder, HoraoEncoder
from horao.persistance.store import Store
from horao.physical.component import CPU, RAM
from horao.physical.computer import Server
from horao.physical.hardware import HardwareList
from horao.physical.network import NIC, Port, Switch, SwitchType
from horao.physical.status import DeviceStatus
from tests.logical.test_scheduler import initialize_logical_infrastructure

pytest_plugins = ("pytest_asyncio",)


def test_direct_encode_decode_lists():
    l = HardwareList[CPU]()
    l.append(
        CPU(
            serial_number="123",
            model="bar",
            number=1,
            clock_speed=1.0,
            cores=1,
            features=None,
        )
    )
    ser = json.dumps(l, cls=HoraoEncoder)
    deser = json.loads(ser, cls=HoraoDecoder)
    assert list(l) == deser


@pytest.mark.asyncio
async def test_storing_loading_logical_clock():
    clock = LogicalClock()
    store = Store(None)
    await store.async_save("clock", clock)
    loaded_clock = await store.async_load("clock")
    assert clock == loaded_clock


@pytest.mark.asyncio
async def test_storing_loading_observed_removed_set():
    observed_removed_set = set()
    observed_removed_set.add("foo")
    observed_removed_set.add("bar")
    store = Store(None)
    await store.async_save("observed_removed_set", observed_removed_set)
    loaded_observed_removed_set = await store.async_load("observed_removed_set")
    assert observed_removed_set == loaded_observed_removed_set


@pytest.mark.asyncio
async def test_storing_loading_last_writer_wins_register():
    lww_register = LastWriterWinsRegister("test", "foo")
    update = lww_register.write("foobar", 1)
    lww_register.update(update)

    store = Store(None)
    await store.async_save("lww_register", lww_register)
    loaded_lww_register = await store.async_load("lww_register")
    assert lww_register == loaded_lww_register


@pytest.mark.asyncio
async def test_storing_loading_last_writer_wins_map():
    lww_map = LastWriterWinsMap()
    name = "foo"
    value = "bar"
    lww_map.set(name, value, 1)
    store = Store(None)
    await store.async_save("lww_map", lww_map)
    loaded_lww_map = await store.async_load("lww_map")
    assert lww_map == loaded_lww_map


@pytest.mark.asyncio
async def test_storing_loading_switch():
    switch = Switch(
        serial_number="123",
        name="foo",
        model="bar",
        number=1,
        layer=LinkLayer.Layer2,
        switch_type=SwitchType.Access,
        status=DeviceStatus.Up,
        managed=False,
        lan_ports=[
            Port(
                serial_number="123",
                model="bar",
                number=1,
                mac="00:00:00:00:00:00",
                status=DeviceStatus.Up,
                connected=False,
                speed_gb=1,
            )
        ],
        uplink_ports=[],
    )
    store = Store(None)
    await store.async_save("switch", switch)
    loaded_switch = await store.async_load("switch")
    assert switch == loaded_switch


@pytest.mark.asyncio
async def test_storing_loading_server():
    server = Server(
        serial_number="123",
        name="foo",
        model="bar",
        number=1,
        cpus=[
            CPU(
                serial_number="123",
                model="bar",
                number=1,
                clock_speed=1.0,
                cores=1,
                features=None,
            )
        ],
        rams=[
            RAM(
                serial_number="123",
                model="bar",
                number=1,
                size_gb=1,
                speed_mhz=1,
            )
        ],
        nics=[
            NIC(
                serial_number="123",
                model="bar",
                number=1,
                ports=[
                    Port(
                        serial_number="123",
                        model="bar",
                        number=1,
                        mac="00:00:00:00:00:00",
                        status=DeviceStatus.Up,
                        connected=False,
                        speed_gb=1,
                    )
                ],
            )
        ],
        disks=[],
        accelerators=[],
        status=DeviceStatus.Up,
    )
    store = Store(None)
    await store.async_save("server", server)
    loaded_server = await store.async_load("server")
    assert server == loaded_server


@pytest.mark.asyncio
async def test_storing_loading_list():
    l = HardwareList[CPU]()
    l.append(
        CPU(
            serial_number="123",
            model="bar",
            number=1,
            clock_speed=1.0,
            cores=1,
            features=None,
        )
    )
    store = Store(None)
    await store.async_save("list", l)
    loaded_list = await store.async_load("list")
    assert list(l) == loaded_list


@pytest.mark.asyncio
async def test_storing_loading_logical_infrastructure():
    dc, dcn = initialize_logical_infrastructure()
    infrastructure = LogicalInfrastructure({dc: [dcn]})
    store = Store(None)
    await store.async_save("infrastructure", infrastructure)
    loaded_infrastructure = await store.async_load("infrastructure")
    assert infrastructure == loaded_infrastructure
