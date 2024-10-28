# -*- coding: utf-8 -*-#
from horao.rbac import Namespace, Permission, Permissions


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


class Student(Permissions):
    def __init__(self):
        super().__init__(
            "Student",
            {Namespace.System: Permission.Read},
        )

    def __str__(self):
        return self.name


class Researcher(Permissions):
    def __init__(self):
        super().__init__(
            "Researcher",
            {Namespace.System: Permission.Read},
        )

    def __str__(self):
        return self.name


class PrincipalInvestigator(Permissions):
    def __init__(self):
        super().__init__(
            "Principal Investigator",
            {Namespace.System: Permission.Read},
        )

    def __str__(self):
        return self.name
