# -*- coding: utf-8 -*-#
"""Role-based access control module for the application."""
from horao.rbac.permission import Permissions, Namespace, Permission


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


class SecurityEngineer(Permissions):
    def __init__(self):
        super().__init__(
            "Security Engineer",
            {Namespace.System: Permission.Write, Namespace.Network: Permission.Write},
        )

    def __str__(self):
        return self.name


class TenantOwner(Permissions):
    def __init__(self):
        super().__init__(
            "TenantOwner",
            {Namespace.System: Permission.Read},
        )

    def __str__(self):
        return self.name


class Delegate(Permissions):
    def __init__(self):
        super().__init__(
            "Delegate",
            {Namespace.System: Permission.Read},
        )

    def __str__(self):
        return self.name
