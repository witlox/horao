# -*- coding: utf-8 -*-#
"""Global test settings"""

import os

import pytest


def pytest_configure():
    os.environ["TELEMETRY"] = "OFF"
    os.environ["ENVIRONMENT"] = "development"
