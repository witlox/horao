import logging

from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import JSONResponse


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

    return JSONResponse(status_code=200, content={"status": "is alive"})
