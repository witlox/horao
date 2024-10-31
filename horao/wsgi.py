# -*- coding: utf-8 -*-#
"""Main entrypoint of the application for ASGI servers."""
from horao import init_api
from a2wsgi import WSGIMiddleware  # type: ignore

ASGI_APP = WSGIMiddleware(init_api())  # type: ignore
