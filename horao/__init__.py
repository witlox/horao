# -*- coding: utf-8 -*-#
"""Main module for the application.

This module is the main module for the application. It initializes the application and the API. The API is defined in
the spec file. The application is defined in the controllers and models. The controllers are responsible for
orchestrating the resources on various control planes in various datacenters. Also instructions for higher level
platforms like Kubernetes, OpenStack, Slurm, Clouds, etc. are defined here. The models are used to model the hardware
and software resources of the system.
"""
import logging
import os
from typing import Optional

from opentelemetry import metrics, trace  # type: ignore
from opentelemetry.instrumentation.logging import LoggingInstrumentor  # type: ignore
from opentelemetry.instrumentation.starlette import (
    StarletteInstrumentor,  # type: ignore
)
from opentelemetry.sdk.metrics import MeterProvider  # type: ignore
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,  # type: ignore
)
from starlette.authentication import AuthenticationBackend

if os.getenv("OLTP_HTTP", "False") == "False":
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,  # type: ignore
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,  # type: ignore
    )
else:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter  # type: ignore

from apiman.starlette import Apiman  # type: ignore
from opentelemetry.sdk.resources import SERVICE_NAME, Resource  # type: ignore
from opentelemetry.sdk.trace import TracerProvider  # type: ignore
from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
from starlette.applications import Starlette  # type: ignore
from starlette.middleware import Middleware  # type: ignore
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware  # type: ignore
from starlette.responses import HTMLResponse  # type: ignore
from starlette.routing import Route  # type: ignore
from starlette.schemas import SchemaGenerator  # type: ignore

import horao.api
import horao.api.synchronization
import horao.auth
from horao.auth.multi import MultiAuthBackend

LoggingInstrumentor().instrument(set_logging_format=True)

resource = Resource.create(
    {
        "service.name": "horao",
        "service.instance.id": os.uname().nodename,
    }
)

if "OLTP_COLLECTOR_URL" in os.environ:
    oltp_url = os.getenv("OLTP_COLLECTOR_URL")
    oltp_insecure = False if os.getenv("OLTP_INSECURE", "False") == "False" else True
    oltp_http = False if os.getenv("OLTP_HTTP", "False") == "False" else True
    trace_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=f"{oltp_url}/v1/traces",
            insecure=oltp_insecure,
        )
        if oltp_http
        else OTLPSpanExporter(
            endpoint=f"{oltp_url}",
            insecure=oltp_insecure,
        )
    )
    trace_provider.add_span_processor(processor)
    trace.set_tracer_provider(trace_provider)

    reader = PeriodicExportingMetricReader(
        (
            OTLPMetricExporter(
                endpoint=f"{oltp_url}/v1/metrics",
                insecure=oltp_insecure,
            )
            if oltp_http
            else OTLPMetricExporter(
                endpoint=f"{oltp_url}",
                insecure=oltp_insecure,
            )
        ),
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)


def init(authorization: Optional[AuthenticationBackend] = None) -> Starlette:
    """
    Initialize the API
    authorization: optional authorization backend to overwrite default behavior (useful for testing)
    :return: app instance
    """
    if os.getenv("DEBUG", "False") == "True":
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("horao.init")
    logger.debug("initializing horao")
    cors = os.getenv("CORS", "*")
    if cors == "*":
        logger.warning("CORS is set to *")
    routes = [
        Route("/login", endpoint=horao.api.authenticate.login, methods=["POST"]),
        Route("/logout", endpoint=horao.api.authenticate.logout, methods=["POST"]),
        Route(
            "/synchronize",
            endpoint=horao.api.synchronization.synchronize,
            methods=["POST"],
        ),
        Route(
            "/reservations",
            endpoint=horao.api.user_actions.get_reservations,
            methods=["GET"],
        ),
        Route(
            "/reservation",
            endpoint=horao.api.user_actions.create_reservation,
            methods=["POST"],
        ),
    ]
    middleware = [
        Middleware(CORSMiddleware, allow_origins=[cors]),
    ]
    if authorization:
        logger.warning(f"Using custom authorization backend: {type(authorization)}")
        middleware.append(Middleware(AuthenticationMiddleware, backend=authorization))
    else:
        middleware.append(
            Middleware(AuthenticationMiddleware, backend=MultiAuthBackend())
        )
    app = Starlette(
        routes=routes,
        middleware=middleware,
        debug=False if os.getenv("DEBUG", "False") == "False" else True,
    )
    if os.getenv("UI", "False") == "True":
        apiman = Apiman(
            title="Horao",
            specification_url="/spec/",
            redoc_url="/docs/",
            template="openapi/openapi.yml",
        )
        apiman.init_app(app)
    if os.getenv("TELEMETRY", "ON") == "OFF":
        logger.warning("Telemetry is turned off")
    else:
        StarletteInstrumentor().instrument_app(app)
    return app
