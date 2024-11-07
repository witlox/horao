# Telemetry

`HORAO` is telemetrised using [OpenTelemetry](https://opentelemetry.io). 
Telemetry is switched on by default, but can be configured turned off by explicitly setting the environment variable `TELEMETRY` to `OFF` (useful for automated tests).

```dotenv 
TELEMETRY=OFF
```

The following sections describe telemetry configuration for `HORAO`.

## Logging level

The logging level can be changed using the `DEBUG` environment variable. The default is `INFO`. 
The logging level can be set in the `.env` file as follows:
```dotenv 
DEBUG=True
```
Be aware that setting the logging level to `DEBUG` will generate a lot of output.

## Sending telemetry to a collector

The telemetry is sent using [OLTP exporter](https://github.com/open-telemetry/opentelemetry-python/tree/main/exporter/opentelemetry-exporter-otlp).
The default protocol is `grpc` this can be switched to `http` by setting the environment variable `OLTP_HTTP` to True.
```dotenv
OLTP_HTTP=True
```
The default mechanism is to send telemetry `securely`, this can be switched to `insecure` by setting the environment variable `OLTP_INSECURE` to True.
```dotenv
OLTP_INSECURE=True
```

A specific collector URL needs to be specified, otherwise the Telemetry will not be sent.
```dotenv
OLTP_COLLECTOR_URL=http://localhost:4317
```

## Various environment variables that can be set to configure telemetry

To exclude certain URLs from tracking
```dotenv
OTEL_PYTHON_STARLETTE_EXCLUDED_URLS="client/.*/info,health"
```
will exclude requests such as https://site/client/123/info and https://site/health from being traced.


To capture HTTP request headers as span attributes
```dotenv
OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST="content-type,custom_request_header"
```
will extract content-type and custom_request_header from the request headers and add them as span attributes.


To capture HTTP response headers as span attributes
```dotenv
OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_RESPONSE="content-type,custom_response_header"
```
will extract content-type and custom_response_header from the response headers and add them as span attributes.

In order to prevent storing sensitive data such as personally identifiable information (PII), session keys, passwords, etc.
```dotenv
OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SANITIZE_FIELDS=".*session.*,set-cookie"
```
will replace the value of headers such as session-id and set-cookie with [REDACTED] in the span.