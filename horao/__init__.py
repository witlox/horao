# -*- coding: utf-8 -*-#
"""Main module for the application.

This module is the main module for the application. It initializes the application and the API. The API is defined in
the spec file. The application is defined in the controllers and models. The controllers are responsible for
orchestrating the resources on various control planes in various datacenters. Also instructions for higher level
platforms like Kubernetes, OpenStack, Slurm, Clouds, etc. are defined here. The models are used to model the hardware
and software resources of the system.
"""
import os
import logging

from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import HTMLResponse
from starlette.routing import Route

import horao.api
import horao.auth
import horao.controllers
import horao.models


from starlette.applications import Starlette  # type: ignore
from starlette.middleware import Middleware  # type: ignore
from starlette.middleware.cors import CORSMiddleware  # type: ignore
from starlette.schemas import SchemaGenerator  # type: ignore
from dotenv import load_dotenv  # type: ignore

from horao.auth.basic_auth import BasicAuthBackend

schemas = SchemaGenerator(
    {"openapi": "3.0.0", "info": {"title": "HORAO API", "version": "1.0"}}
)


def openapi_schema(request):
    return schemas.OpenAPIResponse(request=request)


async def docs(request):
    html = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <title>HORAO - Redoc</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
          </head>
          <body>
            <redoc spec-url="{request.url.scheme}://{request.url.netloc}/openapi.json"></redoc>
            <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"> </script>
          </body>
        </html>
    """
    return HTMLResponse(html)


def init_api() -> Starlette:
    cors = os.getenv("CORS", "*")
    if cors == "*":
        logging.warning("CORS is set to *")
    routes = [
        Route("/ping", endpoint=horao.api.alive_controller.is_alive, methods=["GET"]),
        Route("/openapi.json", endpoint=openapi_schema, include_in_schema=False),
    ]
    module_root = os.path.dirname(os.path.dirname(__file__))
    environment = os.environ.get("ENVIRONMENT", "development")
    dotenv_path = module_root + "/horao/env/" + f".env.{environment}"
    load_dotenv(dotenv_path)
    if bool(os.getenv("UI", False)):
        routes.append(Route("/docs", endpoint=docs, methods=["GET"]))
    middleware = [
        Middleware(CORSMiddleware, allow_origins=[cors]),
    ]
    if os.getenv("AUTH", "basic") == "basic":
        middleware.append(
            Middleware(AuthenticationMiddleware, backend=BasicAuthBackend())
        )
    return Starlette(
        routes=routes, middleware=middleware, debug=bool(os.getenv("DEBUG", False))
    )
