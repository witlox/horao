# -*- coding: utf-8 -*-#
"""Main module for the application."""
from horao import init_api
from a2wsgi import WSGIMiddleware  # type: ignore

ASGI_APP = WSGIMiddleware(init_api())
