# -*- coding: utf-8 -*-#
import pytest

from horao import init_api
from tests import base_url


def test_ping_service():
    ia = init_api()
    with ia.test_client() as client:
        lg = client.get(base_url("ping"))
        assert 200 == lg.status_code
