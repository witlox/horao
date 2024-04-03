# -*- coding: utf-8 -*-#
import logging

from starlette.authentication import requires
from starlette.requests import Request  # type: ignore
from starlette.responses import JSONResponse  # type: ignore


@requires("authenticated")
async def is_alive(request: Request) -> JSONResponse:
    """
    responses:
      200:
        description: alive message.
        examples:
          {"status": "is alive"}
      403:
        description: Unauthorized
    """
    logging.info(f"Calling Keep Alive ({request})")
    return JSONResponse(status_code=200, content={"status": "is alive"})
