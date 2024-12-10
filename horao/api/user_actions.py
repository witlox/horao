# -*- coding: utf-8 -*-#
import json
import logging
import os

from starlette.authentication import requires
from starlette.requests import Request  # type: ignore
from starlette.responses import JSONResponse  # type: ignore

from horao.auth.permissions import Namespace, Permission
from horao.auth.validate import permission_required
from horao.persistance import HoraoEncoder, init_session


@requires("authenticated")
@permission_required(Namespace.User, Permission.Read)
async def get_reservations(request: Request) -> JSONResponse:
    """
    responses:
      200:
        description: reservations for current user.
        examples: [
            {"type": "Reservation",
             "name": "reservation",
             "start": "start timestamp",
             "end": "end timestamp",
             "resources": [],
             "maximal_resources": [],
             "hsn_only": obj.hsn_only,
            }
          ]
      403:
        description: Unauthorized
      500:
        description: Error processing request
    """
    logging.debug(f"Calling Reservations ({request})")
    try:
        session = init_session()
        logical_infrastructure = await session.load_logical_infrastructure()
        claims = []
        for claim in logical_infrastructure.claims:
            if claim.owner == request.user or request.user in claim.delegates:
                claims.append(claim)
        return JSONResponse(
            status_code=200, content={"claims": json.dumps(claims, cls=HoraoEncoder)}
        )
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        if os.getenv("DEBUG", "False") == "True":
            return JSONResponse(
                status_code=500, content={"error": f"Error processing request {str(e)}"}
            )
        return JSONResponse(
            status_code=500, content={"error": f"Error processing request"}
        )
