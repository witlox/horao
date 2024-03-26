# -*- coding: utf-8 -*-#
"""Role-based access control module for the application.

This module contains the classes and functions that are used to authorize the users of the application. The module
only contains authorization. The auth module is used to define the authentication method.
"""
from abc import ABC
from enum import Enum, auto
from typing import Callable, TypeVar, Dict, List

from horao.rbac.mappings import PermissionSession


class User:
    """Simplistic class to map groups to roles."""

    def __init__(self, name: str, groups: List[str]):
        self.name = name
        self.groups = groups

    def roles(self):
        pass


class Permission(Enum):
    """We have two permissions: Read and Write, Write implies read."""

    Read = auto()
    Write = auto()


class Namespace(Enum):
    """Namespaces define where a permission applies"""

    System = auto()
    Network = auto()


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
        return (
            self.permissions[namespace] == Permission.Read
            or self.permissions[namespace] == Permission.Write
        )

    def can_write(self, namespace: Namespace):
        return self.permissions[namespace] == Permission.Write


RT = TypeVar("RT")


class UnauthorizedError(RuntimeError):
    """We raise this exception when a user tries to access a resource without the proper permissions."""

    def __init__(self, user, function: Callable[..., RT], *args: str, **kwargs: int):
        super().__init__("unauthorized access to resource")
        self.user = user
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return f"UnauthorizedError from {self.user}: [{self.function}] - ({self.args} ; {self.kwargs})"


def permission_required(
    namespace: Namespace, permission: Permission
) -> Callable[[Callable[..., RT]], Callable[..., RT]]:
    """
    Decorator to check if a user has the permission to access a resource.
    :param namespace: namespace to check
    :param permission: permission to validate
    :return: function call if the user has the permission
    :raises: UnauthorizedError if the user does not have the permission
    """

    def decorator(func: Callable[..., RT]) -> Callable[..., RT]:
        def wrapper(session: PermissionSession, *args: str, **kwargs: int) -> RT:
            if not session.check_permission(namespace, permission):
                raise UnauthorizedError({session.user}, func, *args, **kwargs)
            return func(session, *args, **kwargs)

        return wrapper

    return decorator
