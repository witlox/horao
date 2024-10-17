# -*- coding: utf-8 -*-#
from horao.models import (
    Switch,
    LinkLayer,
    DeviceStatus,
    Port,
    Server,
    NIC,
    DataCenter,
    Row,
    Cabinet,
)
from horao.models.network import (
    SwitchType,
    DataCenterNetwork,
    NetworkType,
    NetworkTopology,
)
from tests import basic_networking_configuration


def test_network_topology_detection_tree():
    #         core
    #       /      \
    #   leaf        leaf
    # Test the network topology detection
    _, dcn, cs, lsl, lsr, _ = basic_networking_configuration()
    dcn.link(lsl, cs)
    dcn.link(lsr, cs)
    assert dcn.get_topology() == NetworkTopology.Tree


def test_link_server_to_switch_ports_up_unlink_downs():
    dc, dcn, _, lsl, _, srv = basic_networking_configuration()
    server_nic = next(iter(srv.nic), None)
    assert server_nic is not None
    server_nic_port = next(iter(server_nic.ports), None)
    assert server_nic_port is not None
    fetched_server_nic = dc.fetch_server_nic(0, 0, 0, 0, None)
    assert fetched_server_nic.ports is not None
    fetched_server_nic_port = next(iter(fetched_server_nic.ports))
    assert (
        fetched_server_nic_port is not None
        and fetched_server_nic_port == server_nic_port
    )
    dcn.link(fetched_server_nic, lsl)
    assert server_nic_port.status == DeviceStatus.Up
    assert lsl.ports[0].status == DeviceStatus.Up
    dcn.unlink(fetched_server_nic, lsl)
    assert server_nic_port.status == DeviceStatus.Down
    assert lsl.ports[0].status == DeviceStatus.Down


def test_downing_switch_downs_all_ports():
    switch_port = Port(
        "ser4",
        "lp",
        "lsp",
        2,
        "m3.1",
        DeviceStatus.Down,
        False,
        25,
    )
    switch = Switch(
        "ser7",
        "ls2",
        "ls",
        3,
        LinkLayer.Layer2,
        SwitchType.Core,
        DeviceStatus.Up,
        True,
        [switch_port],
        [],
    )
    server_nic_port = Port(
        "srv_port", "srv_port", "srv_port", 1, "m5", DeviceStatus.Down, False, 100
    )
    server_nic = NIC("srv_nic", "srv_nic", "srv_nic", 1, [server_nic_port])
    server = Server(
        "srv",
        "srv",
        "srv",
        1,
        [],
        [],
        [server_nic],
        [],
        [],
        DeviceStatus.Up,
    )
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    dcn.add_multiple([switch, server])
    dcn.link(server_nic, switch)
    assert switch_port.status == DeviceStatus.Up
    assert server_nic_port.status == DeviceStatus.Up
    dcn.toggle(switch)
    assert switch_port.status == DeviceStatus.Down
    assert server_nic_port.status == DeviceStatus.Down
