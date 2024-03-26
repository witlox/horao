# -*- coding: utf-8 -*-#
"""Authorization module for the application.

This module contains the classes and functions that are used to authorize the users of the application. The module
only contains authorization. The RBAC module is used to define the roles and permissions of the users. There are
various implementations that can be used, but some are only meant for development purpose.
"""


class UnauthenticatedError(RuntimeError):
    """We raise this exception when a user cannot be authenticated."""

    def __init__(self, user):
        super().__init__("unauthorized access to resource")
        self.user = user

    def __str__(self):
        return f"UnauthorizedError from {self.user}"
