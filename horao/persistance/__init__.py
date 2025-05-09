# -*- coding: utf-8 -*-#
"""Module containing the persistence layer of the application.

This module contains the classes and functions that are used to interact with the database.
Serialization is done using JSON.
"""
import os

from .serialize import HoraoDecoder, HoraoEncoder
from .store import Store

session = None


def init_session():
    global session
    session = Store(os.getenv("REDIS_URL", None))
    return session
