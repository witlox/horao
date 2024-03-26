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


def test_link_server_to_switch_ports_up():
    dc, dcn, _, lsl, _, srv = basic_networking_configuration()
    server_nic = next(iter(srv.nic), None)
    assert server_nic is not None
    server_nic_port = next(iter(server_nic.lan_ports), None)
    assert server_nic_port is not None
    fetched_server_nic = dc.fetch_server_nic(0, 0, 0, 0, None)
    assert fetched_server_nic.lan_ports is not None
    fetched_server_nic_port = next(iter(fetched_server_nic.lan_ports))
    assert (
        fetched_server_nic_port is not None
        and fetched_server_nic_port == server_nic_port
    )
    dcn.link(fetched_server_nic, lsl)
    assert server_nic_port.status == DeviceStatus.Up


def test_unlink_server_from_switch_downs_ports():
    pass


def test_downing_switch_downs_all_ports():
    pass
