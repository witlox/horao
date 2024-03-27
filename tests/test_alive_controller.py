# -*- coding: utf-8 -*-#
import pytest

from horao import init_api


def test_ping_service_unauthorized():
    ia = init_api()
    with ia.test_client() as client:
        lg = client.get("ping")
        assert 401 == lg.status_code
