# -*- coding: utf-8 -*-#
"""All calls needed for synchronizing HORAO instances."""
import json
import logging

from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import JSONResponse

from horao.persistance import HoraoDecoder, init_session


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
    try:
        logical_infrastructure = json.loads(data, cls=HoraoDecoder)
        session = init_session()
        for k, v in logical_infrastructure.infrastructure.items():
            local_dc = session.load(k.name)
            if not local_dc:
                session.save(k.name, k)
            else:
                local_dc.merge(k)
            local_dc_content = session.load(f"{k.name}.content")
            if not local_dc_content:
                session.save(f"{k.name}.content", v)
            else:
                local_dc_content.merge(v)
    except Exception as e:
        logging.error(f"Error synchronizing: {e}")
        return JSONResponse(status_code=400, content={"error": "Error synchronizing"})
    return JSONResponse(status_code=200, content={"status": "is alive"})
