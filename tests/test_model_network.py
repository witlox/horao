# -*- coding: utf-8 -*-#
from horao.models import Switch, LinkLayer, DeviceStatus, Port, Server, NIC, DataCenter, Row, Cabinet
from horao.models.network import (
    SwitchType,
    DataCenterNetwork,
    NetworkType,
    NetworkTopology,
)


def test_network_topology_detection_tree():
    #         core
    #       /      \
    #   leaf        leaf
    # Test the network topology detection
    core_port_left = Port(
        "core_port_left",
        "core_port_left",
        "core_port_left",
        1,
        "mac",
        DeviceStatus.Up,
        100,
    )
    core_port_right = Port(
        "core_port_right",
        "core_port_right",
        "core_port_right",
        1,
        "mac1",
        DeviceStatus.Up,
        100,
    )
    core = Switch(
        "core",
        "core",
        "core",
        1,
        LinkLayer.Layer2,
        SwitchType.Core,
        DeviceStatus.Up,
        True,
        [core_port_left, core_port_right],
        [],
    )
    leaf_left_uplink_port = Port(
        "leaf_left_uplink_port",
        "leaf_uplink_port",
        "leaf_uplink_port",
        1,
        "mac2",
        DeviceStatus.Up,
        100,
    )
    leaf_left = Switch(
        "leaf_left",
        "leaf_left",
        "leaf_left",
        1,
        LinkLayer.Layer2,
        SwitchType.Core,
        DeviceStatus.Up,
        True,
        [],
        [leaf_left_uplink_port],
    )
    leaf_right_uplink_port = Port(
        "leaf_right_uplink_port",
        "leaf_right_uplink_port",
        "leaf_right_uplink_port",
        1,
        "mac3",
        DeviceStatus.Up,
        100,
    )
    leaf_right = Switch(
        "leaf_right",
        "leaf_right",
        "leaf_right",
        1,
        LinkLayer.Layer2,
        SwitchType.Core,
        DeviceStatus.Up,
        True,
        [],
        [leaf_right_uplink_port],
    )
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    dcn.add_multiple([core, leaf_left, leaf_right])
    dcn.link(leaf_left, core)
    dcn.link(leaf_right, core)
    assert dcn.get_topology() == NetworkTopology.Tree


def test_link_server_to_switch_ports_up():
    server_nic_port = Port("srv_port", "srv_port", "srv_port", 1, "mac", DeviceStatus.Down, 100)
    server_nic = NIC("srv_nic", "srv_nic", "srv_nic", 1, [server_nic_port])
    server = Server("srv", "srv", "srv", 1, [], [], [server_nic], [], [], DeviceStatus.Up)
    switch_port = Port("sw_port", "sw_port", "sw_port", 1, "mac", DeviceStatus.Down, 100)
    switch = Switch("sw", "sw", "sw", 1, LinkLayer.Layer2, SwitchType.Access, DeviceStatus.Up, True, [switch_port], [])
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    dc = DataCenter("dc", 1, [Row("row", 1, [Cabinet("cab", "cab", "cab", 1, [server], [], [switch])])])
    fetched_server_nic = dc.fetch_server_nic(0, 0, 0, 0)
    assert fetched_server_nic.lan_ports is not None
    fetched_server_nic_port = next(iter(fetched_server_nic.lan_ports))
    assert fetched_server_nic_port is not None and fetched_server_nic_port == server_nic_port
    dcn.link(fetched_server_nic, switch)
    assert server_nic_port.status == DeviceStatus.Up and switch_port.status == DeviceStatus.Up
