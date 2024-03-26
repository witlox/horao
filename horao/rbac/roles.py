# -*- coding: utf-8 -*-#
from horao.rbac import Permissions, Permission, Namespace


class NetworkEngineer(Permissions):
    def __init__(self):
        super().__init__(
            "Network Engineer",
            {Namespace.Network: Permission.Write, Namespace.System: Permission.Read},
        )

    def __str__(self):
        return self.name


class SystemEngineer(Permissions):
    def __init__(self):
        super().__init__(
            "System Engineer",
            {Namespace.System: Permission.Write, Namespace.Network: Permission.Read},
        )

    def __str__(self):
        return self.name
