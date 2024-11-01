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

from opentelemetry import metrics, trace  # type: ignore
from opentelemetry.instrumentation.logging import LoggingInstrumentor  # type: ignore
from opentelemetry.instrumentation.starlette import (
    StarletteInstrumentor,  # type: ignore
)
from opentelemetry.sdk.metrics import MeterProvider  # type: ignore
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,  # type: ignore
)

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
from horao.auth.basic_auth import BasicAuthBackend
from horao.auth.peer import PeerAuthBackend

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
    """
    Initialize the API
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
        Route("/ping", endpoint=horao.api.alive_controller.is_alive, methods=["GET"]),
        Route(
            "/synchronize",
            endpoint=horao.api.synchronization.synchronize,
            methods=["POST"],
        ),
        Route("/openapi.json", endpoint=openapi_schema, include_in_schema=False),
    ]
    if os.getenv("UI", "False") == "True":
        routes.append(Route("/docs", endpoint=docs, methods=["GET"]))
    middleware = [
        Middleware(CORSMiddleware, allow_origins=[cors]),
        Middleware(AuthenticationMiddleware, backend=PeerAuthBackend()),
    ]
    if os.getenv("AUTH", "basic") == "basic":
        middleware.append(
            Middleware(AuthenticationMiddleware, backend=BasicAuthBackend())
        )
    if os.getenv("TELEMETRY", "ON") == "OFF":
        logger.warning("Telemetry is turned off")
        return Starlette(
            routes=routes,
            middleware=middleware,
            debug=False if os.getenv("DEBUG", "False") == "False" else True,
        )
    return StarletteInstrumentor.instrument_app(
        Starlette(
            routes=routes,
            middleware=middleware,
            debug=False if os.getenv("DEBUG", "False") == "False" else True,
        )
    )
