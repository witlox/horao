# -*- coding: utf-8 -*-#
"""Authorization module for the application.

This module contains the classes and functions that are used to authorize the users of the application. The module
only contains authorization. The RBAC module is used to define the roles and permissions of the users. There are
various implementations that can be used, but some are only meant for development purpose.
"""
from horao.auth.basic import BasicAuthBackend
from horao.auth.multi import MultiAuthBackend, Peer
