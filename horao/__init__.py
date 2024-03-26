# -*- coding: utf-8 -*-#
"""Main module for the application.

This module is the main module for the application. It initializes the application and the API. The API is defined in
the swagger file. The application is defined in the controllers and models. The controllers are responsible for
orchestrating the resources on various control planes in various datacenters. Also instructions for higher level
platforms like Kubernetes, OpenStack, Slurm, Clouds, etc. are defined here. The models are used to model the hardware
and software resources of the system.
"""
import os

import horao.api
import horao.controllers
import horao.models

from connexion import AsyncApp  # type: ignore
from connexion.options import SwaggerUIOptions  # type: ignore
from dotenv import load_dotenv  # type: ignore


environment = os.environ.get("ENVIRONMENT", "development")
dotenv_path = f".env.{environment}"


def init_api():
    load_dotenv(dotenv_path)
    options = (
        SwaggerUIOptions(swagger_ui_path="/docs")
        if bool(os.getenv("UI", False))
        else SwaggerUIOptions()
    )
    app = AsyncApp(__name__, swagger_ui_options=options)
    if environment == "development":
        app.add_api(
            "./swagger/swagger-development.yaml",
            arguments={"debug": bool(os.getenv("DEBUG", False))},
            swagger_ui_options=options,
        )
    else:
        app.add_api("./swagger/swagger-production.yaml", swagger_ui_options=options)
    return app
