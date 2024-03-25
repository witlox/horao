# -*- coding: utf-8 -*-#
from horao.models import Switch, LinkLayer, DeviceStatus, Port
from horao.models.network import SwitchType, DataCenterNetwork, NetworkType, NetworkTopology


def test_network_topology_detection_tree():
    #          core
    #       /       \
    #  leaf          leaf
    # Test the network topology detection
    core_port_left = Port("core_port_left", "core_port_left", "core_port_left", 1, LinkLayer.Layer2, DeviceStatus.Up, 100)
    core_port_right = Port("core_port_right", "core_port_right", "core_port_right", 1, LinkLayer.Layer2, DeviceStatus.Up, 100)
    core = Switch("core", "core", "core", 1, LinkLayer.Layer2, SwitchType.Core, DeviceStatus.Up, True, [core_port_left, core_port_right], [])
    leaf_left_uplink_port = Port("leaf_left_uplink_port", "leaf_uplink_port", "leaf_uplink_port", 1, LinkLayer.Layer2, DeviceStatus.Up, 100)
    leaf_left = Switch("leaf_left", "leaf_left", "leaf_left", 1, LinkLayer.Layer2, SwitchType.Core, DeviceStatus.Up, True, [], [leaf_left_uplink_port])
    leaf_right_uplink_port = Port("leaf_right_uplink_port", "leaf_right_uplink_port", "leaf_right_uplink_port", 1, LinkLayer.Layer2, DeviceStatus.Up, 100)
    leaf_right = Switch("leaf_right", "leaf_right", "leaf_right", 1, LinkLayer.Layer2, SwitchType.Core, DeviceStatus.Up, True, [], [leaf_right_uplink_port])
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    dcn.add_multiple([core, leaf_left, leaf_right])
    dcn.link(leaf_left, core)
    dcn.link(leaf_right, core)
    assert dcn.get_topology() == NetworkTopology.Tree
