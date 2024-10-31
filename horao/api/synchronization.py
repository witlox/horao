# -*- coding: utf-8 -*-#
"""All calls needed for synchronizing HORAO instances."""
import json
import logging

from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import JSONResponse

from horao.persistance import init_session, HoraoDecoder


@requires("peer")
async def synchronize(request: Request) -> JSONResponse:
    """
    responses:
      200:
        description: synchronize logical infrastructures.
        examples:
          {"LogicalInfrastructure": b"ASc3dGJhcg=="}
      403:
        description: Unauthorized
    """
    logging.debug(f"Calling Synchronize ({request})")
    try:
        data = await request.json()
    except Exception as e:
        logging.error(f"Error parsing request: {e}")
        return JSONResponse(status_code=400, content={"error": "Error parsing request"})
    logical_infrastructure = json.loads(data, cls=HoraoDecoder)
    session = init_session()
    for k, v in logical_infrastructure.infrastructure.items():
        pass
    session.load("logical_infrastructure")

    return JSONResponse(status_code=200, content={"status": "is alive"})
