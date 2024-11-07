# -*- coding: utf-8 -*-#
"""Role-based access control module for the application."""
from typing import List, Optional

from starlette.authentication import BaseUser

from horao.auth.permissions import (
    AdministratorPermissions,
    PeerPermissions,
    Permissions,
    TenantPermissions,
)
from horao.conceptual.tenant import Tenant


class User(BaseUser):
    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def identity(self) -> str:
        return self.name

    @property
    def is_admin(self) -> bool:
        return False

    @property
    def permissions(self) -> List[Permissions]:
        return []

    def __str__(self) -> str:
        return self.name


class Peer(User):
    def __init__(self, identity: str, token: str, payload, origin: str) -> None:
        super().__init__(identity)
        self.token = token
        self.payload = payload
        self.origin = origin

    @property
    def has_clean_origin(self) -> bool:
        """
        Check if the identity matches the origin.
        :return: bool
        """
        return self.name == self.origin

    @property
    def permissions(self) -> List[Permissions]:
        return [PeerPermissions()]

    def __str__(self) -> str:
        return f"{self.origin} -> {self.name}"


class TenantController(User):
    def __init__(self, name: str, tenants: Optional[List[Tenant]]) -> None:
        super().__init__(name)
        self.tenants = tenants

    @property
    def permissions(self) -> List[Permissions]:
        return [TenantPermissions()]


class Administrator(User):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    @property
    def is_admin(self) -> bool:
        return True

    @property
    def permissions(self) -> List[Permissions]:
        return [AdministratorPermissions()]
