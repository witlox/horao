# -*- coding: utf-8 -*-#
from horao.rbac import PermissionSet, Namespace, Permission


class PermissionSession:

    def __init__(self, user):
        self.user = user
        self.active_roles = {}

    def add_role(self, role: PermissionSet):
        self.active_roles[role.name] = role

    def drop_role(self, role):
        del self.active_roles[role.name]

    def check_permission(self, namespace: Namespace, permission: Permission):
        """
        Check if the user has the permission to access the namespace given the permission.
        :param namespace: Namespace to validate
        :param permission: Permission to check
        :return: True if the user has the permission, False otherwise
        """
        if permission.Read:
            return any(
                [
                    p
                    for p in self.active_roles.values()
                    if p.namespace == namespace and p.can_read()
                ]
            )
        elif permission.Write:
            return any(
                [
                    p
                    for p in self.active_roles.values()
                    if p.namespace == namespace and p.can_write()
                ]
            )
        else:
            return False

    def __str__(self):
        return f"{self.user} : {self.active_roles.keys()}"


class SessionBuilder:
    pass
