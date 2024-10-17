# -*- coding: utf-8 -*-#
import os
from base64 import b64encode

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
)


os.environ["ENVIRONMENT"] = "development"


def basic_auth(username, password) -> str:
    """
    This function returns a basic auth token for the given username and password
    :param username: user
    :param password: pass
    :return: token
    """
    token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def basic_networking_configuration():
    """
    This function returns a basic networking configuration for testing purposes
    :return: tuple of DataCenter, DataCenterNetwork, (core) Switch, (leaf) Switch, (leaf) Switch, Server
    """
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
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    dcn.add_multiple([core, leaf_left, leaf_right])
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
    dc = DataCenter(
        "dc",
        1,
        [
            Row(
                "row",
                1,
                [
                    Cabinet(
                        "cab",
                        "cab",
                        "cab",
                        1,
                        [server],
                        [],
                        [core, leaf_left, leaf_right],
                    )
                ],
            )
        ],
    )
    return dc, dcn, core, leaf_left, leaf_right, server
