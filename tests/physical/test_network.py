# -*- coding: utf-8 -*-#
import os

from horao.conceptual.osi_layers import LinkLayer
from horao.logical.data_center import DataCenterNetwork, DataCenter
from horao.physical.composite import Cabinet
from horao.physical.computer import Server
from horao.physical.network import (
    NetworkTopology,
    NetworkType,
    SwitchType,
    Port,
    Switch,
    NIC,
)
from horao.physical.status import DeviceStatus

os.environ["ENVIRONMENT"] = "development"


core_port_left = Port("ser1", "cp1", "csp", 1, "m1", DeviceStatus.Down, False, 100)
core_port_right = Port("ser2", "cp2", "csp", 2, "m2", DeviceStatus.Down, False, 100)
core = Switch(
    "ser3",
    "core",
    "cs",
    1,
    LinkLayer.Layer2,
    SwitchType.Core,
    DeviceStatus.Up,
    True,
    [core_port_left, core_port_right],
    [],
)
leaf_left = Switch(
    "ser5",
    "ls1",
    "ls",
    2,
    LinkLayer.Layer2,
    SwitchType.Core,
    DeviceStatus.Up,
    True,
    [
        Port(
            "ser4",
            "lp",
            "lsp",
            2,
            "m3.1",
            DeviceStatus.Down,
            False,
            25,
        )
    ],
    [
        Port(
            "ser4",
            "lp",
            "lsp",
            1,
            "m3",
            DeviceStatus.Down,
            False,
            100,
        )
    ],
)
leaf_right = Switch(
    "ser7",
    "ls2",
    "ls",
    3,
    LinkLayer.Layer2,
    SwitchType.Core,
    DeviceStatus.Up,
    True,
    [
        Port(
            "ser4",
            "lp",
            "lsp",
            2,
            "m3.1",
            DeviceStatus.Down,
            False,
            25,
        )
    ],
    [Port("ser6", "lp1", "lsp", 1, "m4", DeviceStatus.Down, False, 100)],
)

server_nic_port = Port(
    "srv_port", "srv_port", "srv_port", 1, "m5", DeviceStatus.Down, False, 100
)
server = Server(
    "srv",
    "srv",
    "srv",
    1,
    [],
    [],
    [NIC("srv_nic", "srv_nic", "srv_nic", 1, [server_nic_port])],
    [],
    [],
    DeviceStatus.Up,
)


def test_network_topology_detection_tree():
    #         core
    #       /      \
    #   leaf        leaf
    # Test the network topology detection
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    dcn.add_multiple([core, leaf_left, leaf_right])
    dcn.link(leaf_left, core)
    dcn.link(leaf_right, core)
    assert dcn.get_topology() == NetworkTopology.Tree


def test_link_server_to_switch_ports_up_unlink_downs():
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    dcn.add_multiple([core, leaf_left, leaf_right])
    dc = DataCenter("dc", 1)
    dc[1] = [
        Cabinet(
            "cab",
            "cab",
            "cab",
            1,
            [server],
            [],
            [core, leaf_left, leaf_right],
        )
    ]
    server_nic = next(iter(server.nics), None)
    assert server_nic is not None
    snp = next(iter(server_nic.ports), None)
    assert snp is not None
    fetched_server_nic = dc.fetch_server_nic(1, 1, 1, 1, None)
    assert fetched_server_nic.ports is not None
    fetched_server_nic_port = next(iter(fetched_server_nic.ports))
    assert fetched_server_nic_port is not None and fetched_server_nic_port == snp
    dcn.link(fetched_server_nic, leaf_left)
    assert server_nic_port.status == DeviceStatus.Up
    assert leaf_left.ports[0].status == DeviceStatus.Up
    dcn.unlink(fetched_server_nic, leaf_left)
    assert server_nic_port.status == DeviceStatus.Down
    assert leaf_left.ports[0].status == DeviceStatus.Down


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
