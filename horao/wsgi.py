# -*- coding: utf-8 -*-#
from horao import init_api
from a2wsgi import WSGIMiddleware  # type: ignore

ASGI_APP = WSGIMiddleware(init_api().app)
