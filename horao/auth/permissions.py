# -*- coding: utf-8 -*-#
"""Permission classes and functions for the role-based access control module."""
from __future__ import annotations

from abc import ABC
from enum import Enum, auto
from typing import Dict, TypeVar

RT = TypeVar("RT")


class Namespace(Enum):
    """Namespaces define where a permission applies"""

    System = auto()
    User = auto()
    Peer = auto()


class Permission(Enum):
    """We have two permissions: Read and Write, Write implies read."""

    Read = auto()
    Write = auto()


class Permissions(ABC):
    def __init__(self, name: str, permissions: Dict[Namespace, Permission]):
        self.name = name
        self.permissions: Dict[Namespace, Permission] = permissions

    def __len__(self):
        return len(self.permissions.keys())

    def __repr__(self):
        return f"<Permissions {self.name}>"

    def __iter__(self):
        for permission in self.permissions:
            yield permission

    def can_read(self, namespace: Namespace):
        if namespace not in self.permissions.keys():
            return False
        return (
            self.permissions[namespace] == Permission.Read
            or self.permissions[namespace] == Permission.Write
        )

    def can_write(self, namespace: Namespace):
        if namespace not in self.permissions.keys():
            return False
        return self.permissions[namespace] == Permission.Write


class AdministratorPermissions(Permissions):
    def __init__(self):
        super().__init__(
            "System Administrator",
            {Namespace.System: Permission.Write, Namespace.User: Permission.Read},
        )

    def __str__(self):
        return self.name


class PeerPermissions(Permissions):
    def __init__(self):
        super().__init__(
            "Peer Node",
            {Namespace.Peer: Permission.Write},
        )

    def __str__(self):
        return self.name


class TenantPermissions(Permissions):
    def __init__(self):
        super().__init__(
            "TenantOwner",
            {Namespace.System: Permission.Read, Namespace.User: Permission.Write},
        )

    def __str__(self):
        return self.name
