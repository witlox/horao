# -*- coding: utf-8 -*-#
import pytest

from horao import init_api
from tests import base_url


@pytest.fixture(scope="module")
def client():
    ia = init_api()
    with ia.test_client() as c:
        yield c


def test_ping_service(client):
    lg = client.get(base_url("ping"))
    assert 200 == lg.status_code
