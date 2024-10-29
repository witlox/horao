# -*- coding: utf-8 -*-#
"""Role-based access control module for the application.

This module contains the classes and functions that are used to authorize the users of the application. The module
only contains authorization. The auth module is used to define the authentication method.
"""
from .permission import (
    Permissions,
    Namespace,
    Permission,
    PermissionSession,
    User,
    permission_required,
    UnauthorizedError,
)
from .roles import (
    NetworkEngineer,
    SystemEngineer,
    SecurityEngineer,
    TenantOwner,
    Delegate,
)
