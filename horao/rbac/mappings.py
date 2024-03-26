# -*- coding: utf-8 -*-#
from typing import List

from horao.rbac import Permissions, Namespace, Permission, User


class PermissionSession:

    def __init__(self, user: User, permissions: List[Permissions]):
        self.user = user
        self.permissions = permissions

    def check_permission(self, namespace: Namespace, permission: Permission):
        """
        Check if the user has the permission to access the namespace given the permission.
        :param namespace: Namespace to validate
        :param permission: Permission to check
        :return: True if the user has the permission, False otherwise
        """
        if permission.Read:
            return any([p for p in self.permissions if p.can_read(namespace)])
        elif permission.Write:
            return any([p for p in self.permissions if p.can_write(namespace)])
        else:
            return False

    def __str__(self):
        return f"{self.user} : {', '.join([p.name for p in self.permissions])}"


class SessionBuilder:
    pass
