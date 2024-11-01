from horao.conceptual.osi_layers import LinkLayer
from horao.logical.data_center import DataCenter, DataCenterNetwork
from horao.physical.component import CPU, RAM
from horao.physical.composite import Cabinet
from horao.physical.computer import Server
from horao.physical.network import NIC, NetworkType, Port, Switch, SwitchType
from horao.physical.status import DeviceStatus


def initialize_logical_infrastructure():
    dcn = DataCenterNetwork("dcn", NetworkType.Data)
    core_switch = Switch(
        "1",
        "1",
        "core",
        1,
        LinkLayer.Layer2,
        SwitchType.Core,
        DeviceStatus.Up,
        True,
        [
            Port("1", "1", 1, "1", DeviceStatus.Up, False, 100),
            Port("1", "2", 2, "2", DeviceStatus.Up, False, 100),
        ],
        [],
    )
    server1 = Server(
        "1",
        "1",
        "server",
        1,
        [CPU("1", "1", 1, 2.4, 4, None), CPU("1", "1", 2, 2.4, 4, None)],
        [
            RAM("1", "1", 1, 16, None),
            RAM("1", "1", 2, 16, None),
            RAM("1", "1", 3, 16, None),
        ],
        [
            NIC(
                "1",
                "1",
                1,
                [Port("1", "1", 1, "1", DeviceStatus.Up, False, 100)],
            )
        ],
        [],
        [],
        DeviceStatus.Up,
    )
    server2 = Server(
        "2",
        "1",
        "server",
        2,
        [CPU("1", "1", 1, 2.4, 4, None), CPU("1", "1", 2, 2.4, 4, None)],
        [
            RAM("1", "1", 1, 16, None),
            RAM("1", "1", 2, 16, None),
            RAM("1", "1", 3, 16, None),
        ],
        [
            NIC(
                "1",
                "1",
                1,
                [Port("1", "1", 1, "1", DeviceStatus.Up, False, 100)],
            )
        ],
        [],
        [],
        DeviceStatus.Up,
    )
    dc = DataCenter("dc", 1)
    dc[1] = [Cabinet("1", "1", "1", 1, [server1, server2], [], [core_switch])]
    dcn.add(core_switch)
    dcn.add(server1)
    dcn.add(server2)
    dcn.link(core_switch, server1)
    dcn.link(core_switch, server2)
    return dc, dcn
