import inspect
import logging
from functools import wraps

from opentelemetry import trace


def instrument_class_function(
    name: str = None,
    level: int = logging.INFO,
):
    """
    Decorator to instrument a class method with logging and tracing.
    :param name: name of the tracer
    :param level: logging level to use for tracer
    :return: function
    """
    t = trace.get_tracer_provider().get_tracer(name)

    def inner(func):
        @wraps(func)
        def instrumented_logging(*args, **kwargs):
            with t.start_as_current_span(name):
                if level >= logging.getLogger().getEffectiveLevel():
                    current_span = trace.get_current_span()
                    current_span.add_event(
                        f"{inspect.currentframe().f_code.co_name} span"
                    )
                    logging.getLogger().log(level, f"Started {func.__name__}")
                    result = func(*args, **kwargs)
                    logging.getLogger().log(
                        level, f"Finished {func.__name__} with result {result}"
                    )
                    return result
            return func(*args, **kwargs)

        return instrumented_logging

    return inner
