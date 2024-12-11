# -*- coding: utf-8 -*-#
import json
import logging
import os

from starlette.authentication import requires
from starlette.requests import Request  # type: ignore
from starlette.responses import JSONResponse  # type: ignore

from horao.auth.permissions import Namespace, Permission
from horao.auth.validate import permission_required
from horao.logical.scheduler import Scheduler
from horao.persistance import HoraoDecoder, HoraoEncoder, init_session


@requires("authenticated")
@permission_required(Namespace.User, Permission.Read)
async def get_reservations(request: Request) -> JSONResponse:
    """
    reservations
    ---
    get:
      summary: reservations
      description: Get reservations for current user
      tags:
      - user
      responses:
        "200":
          description: Reservations for current user
          content:
            application/json:
              schema:
                type: object
                properties:
                    claims:
                      type: array
                      items:
                        schema:
                          type: object
                          properties:
                            name:
                              type: string
                            start:
                              type: string
                            end:
                              type: string
                            resources:
                              type: array
                              items:
                                type: string
                            maximal_resources:
                              type: array
                              items:
                                type: string
                            hsn_only:
                              type: boolean
        "403":
          description: Unauthorized
        "500":
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


@requires("authenticated")
@permission_required(Namespace.User, Permission.Write)
async def create_reservation(request: Request) -> JSONResponse:
    """
    reservation
    ---
    post:
      summary: reservation
      description: Create a reservation
      tags:
      - user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                start:
                  type: string
                end:
                  type: string
                resources:
                  type: array
                  items:
                    type: string
                maximal_resources:
                  type: array
                  items:
                    type: string
                hsn_only:
                  type: boolean
              example:
                name: "r01"
                start: "start timestamp"
                end: "end timestamp"
                resources: []
                maximal_resources: []
                hsn_only: False
      responses:
        "200":
          description: Reservation created
        "400":
          description: Error parsing request
        "403":
          description: Unauthorized
        "500":
          description: Error processing reservation
    """
    logging.debug(f"Calling Reservations ({request})")
    try:
        data = await request.json()
        claim = json.loads(data, cls=HoraoDecoder)
    except Exception as e:
        logging.error(f"Error parsing request: {e}")
        if os.getenv("DEBUG", "False") == "True":
            return JSONResponse(
                status_code=400, content={"error": f"Error parsing request {str(e)}"}
            )
        return JSONResponse(status_code=400, content={"error": "Error parsing request"})
    try:
        session = init_session()
        logical_infrastructure = await session.load_logical_infrastructure()
        scheduler = Scheduler(logical_infrastructure)
        user = request.user
        start = scheduler.schedule(claim, user.tenant)
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        if os.getenv("DEBUG", "False") == "True":
            return JSONResponse(
                status_code=500, content={"error": f"Error processing request {str(e)}"}
            )
        return JSONResponse(
            status_code=500, content={"error": f"Error processing request"}
        )
    return JSONResponse(
        status_code=200,
        content={"reservation_start": json.dumps(start, cls=HoraoEncoder)},
    )
