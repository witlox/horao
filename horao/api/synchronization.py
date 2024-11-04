# -*- coding: utf-8 -*-#
"""All calls needed for synchronizing HORAO instances."""
import json
import logging
import os

from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import JSONResponse

from horao.persistance import HoraoDecoder, init_session


@requires("authenticated_peer")
async def synchronize(request: Request) -> JSONResponse:
    """
    responses:
      200:
        description: synchronize logical infrastructures.
        examples:
          { "LogicalInfrastructure": {
            "type": "LogicalInfrastructure",
            "infrastructure": {},
            "constraints": {},
            "claims": {},
          }}
      400:
        description: Error parsing request
      403:
        description: Unauthorized
      500:
        description: Error synchronizing
    """
    logging.debug(f"Calling Synchronize ({request})")
    try:
        data = await request.body()
        logical_infrastructure = json.loads(data, cls=HoraoDecoder)
    except Exception as e:
        logging.error(f"Error parsing request: {e}")
        if os.getenv("DEBUG", "False") == "True":
            return JSONResponse(
                status_code=400, content={"error": f"Error parsing request {str(e)}"}
            )
        return JSONResponse(status_code=400, content={"error": "Error parsing request"})
    try:
        session = init_session()
        for k, v in logical_infrastructure.infrastructure.items():
            local_dc = session.load(k.identity)
            if not local_dc:
                session.save(k.identity, k)
            else:
                local_dc.merge(k)
            local_dc_content = session.load(f"{k.identity}.content")
            if not local_dc_content:
                session.save(f"{k.identity}.content", v)
            else:
                local_dc_content.merge(v)
    except Exception as e:
        logging.error(f"Error synchronizing: {e}")
        if os.getenv("DEBUG", "False") == "True":
            return JSONResponse(
                status_code=500, content={"error": f"Error synchronizing {str(e)}"}
            )
        return JSONResponse(status_code=500, content={"error": f"Error synchronizing"})
    return JSONResponse(status_code=200, content={"status": "is alive"})
