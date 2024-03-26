# -*- coding: utf-8 -*-#
from enum import Enum, auto
from functools import wraps
from typing import Callable, ParamSpec, TypeVar, Dict

from horao.rbac.mappings import PermissionSession

Param = ParamSpec("Param")
RetType = TypeVar("RetType")


class Permission(Enum):
    """
    We have two permissions: Read and Write, Write implies read.
    """

    Read = auto()
    Write = auto()


class Namespace(Enum):
    """
    Namespaces define where a permission applies
    """

    System = auto()
    Network = auto()


class PermissionSet:
    def __init__(self, name: str):
        self.name = name
        self.permissions: Dict[Namespace, Permission] = dict()

    def add(self, namespace: Namespace, permission: Permission):
        self.permissions[namespace] = permission

    def can_read(self, namespace: Namespace):
        return (
            self.permissions[namespace] == Permission.Read
            or self.permissions[namespace] == Permission.Write
        )

    def can_write(self, namespace: Namespace):
        return self.permissions[namespace] == Permission.Write


class UnauthorizedError(RuntimeError):
    """We raise this exception when a user tries to access a resource without the proper permissions."""

    def __init__(self, user, function, *args, **kwargs):
        super().__init__("unauthorized access to resource")
        self.user = user
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return f"UnauthorizedError from {self.user}: [{self.function}] - ({self.args} ; {self.kwargs})"


def permission_required(namespace: Namespace, permission: Permission):
    """
    Decorator to check if a user has the permission to access a resource.
    :param namespace: namespace to check
    :param permission: permission to validate
    :return: function call if the user has the permission
    :raises: UnauthorizedError if the user does not have the permission
    """

    def decorator(func: Callable[Param, RetType]):
        @wraps(func)
        def wrap(session: PermissionSession, *args: str, **kwargs: int) -> RetType:
            if not session.check_permission(namespace, permission):
                raise UnauthorizedError({session.user}, func.__name__, *args, **kwargs)
            return func(session, *args, **kwargs)

        return wrap

    return decorator
