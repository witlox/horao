# -*- coding: utf-8 -*-#
from horao.rbac import PermissionSet, Permission, Namespace


class NetworkEngineer(PermissionSet):
    def __init__(self):
        super().__init__("Network Engineer")
        self.add(Namespace.Network, Permission.Write)
        self.add(Namespace.System, Permission.Read)

    def __str__(self):
        return self.name


class SystemEngineer(PermissionSet):
    def __init__(self):
        super().__init__("System Engineer")
        self.add(Namespace.System, Permission.Write)
        self.add(Namespace.Network, Permission.Read)

    def __str__(self):
        return self.name
