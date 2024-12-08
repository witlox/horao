# -*- coding: utf-8 -*-#
"""All calls needed for synchronizing HORAO instances."""
import json
import logging
import os

from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import JSONResponse

from horao.auth.permissions import Namespace, Permission
from horao.auth.validate import permission_required
from horao.persistance import HoraoDecoder, init_session


@requires("authenticated")
@permission_required(Namespace.Peer, Permission.Write)
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
        data = await request.json()
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
            local_dc = await session.async_load(k.name)
            if not local_dc:
                await session.async_save(k.name, k)
            else:
                local_dc.merge(k)
            local_dc_content = await session.async_load(f"{k.name}.content")
            if not local_dc_content:
                await session.async_save(f"{k.name}.content", v)
            else:
                local_dc_content.merge(v)
        if logical_infrastructure.claims:
            for k, v in logical_infrastructure.claims.items():
                await session.async_save(k.name, k)
        if logical_infrastructure.constraints:
            for k, v in logical_infrastructure.contraints.items():
                await session.async_save(k.name, k)
    except Exception as e:
        logging.error(f"Error synchronizing: {e}")
        if os.getenv("DEBUG", "False") == "True":
            return JSONResponse(
                status_code=500, content={"error": f"Error synchronizing {str(e)}"}
            )
        return JSONResponse(status_code=500, content={"error": f"Error synchronizing"})
    return JSONResponse(status_code=200, content={"status": "is alive"})
