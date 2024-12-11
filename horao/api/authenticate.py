# -*- coding: utf-8 -*-#
import os

from authlib.integrations.starlette_client import OAuth  # type: ignore
from starlette.authentication import requires
from starlette.requests import Request
from starlette.responses import RedirectResponse


async def login(request: Request):
    """
    login
    ---
    post:
      summary: login
      description: Login with OpenID Connect
      responses:
        "401":
          description: Not authorized
        "302":
          description: Redirect after successful login
    """
    redirect_uri = request.url_for("auth")
    oauth_role_uri = os.getenv("OAUTH_ROLE_URI", "role")
    oauth_settings = {
        "name": os.getenv("OATH_NAME", "openidc"),
        "client_id": os.getenv("OAUTH_CLIENT_ID"),
        "client_secret": os.getenv("OAUTH_CLIENT_SECRET"),
        "server_metadata_url": os.getenv("OAUTH_SERVER_METADATA_URL", None),
        "api_base_url": os.getenv("OAUTH_API_BASE_URL", None),
        "authorize_url": os.getenv("OAUTH_AUTHORIZE_URL", None),
        "authorize_params": os.getenv("OAUTH_AUTHORIZE_PARAMS", None),
        "access_token_url": os.getenv("OAUTH_ACCESS_TOKEN_URL", None),
        "access_token_params": os.getenv("OAUTH_ACCESS_TOKEN_PARAMS", None),
        "request_token_url": os.getenv("OAUTH_REFRESH_TOKEN_URL", None),
        "request_token_params": os.getenv("OAUTH_REFRESH_TOKEN_PARAMS", None),
        "client_kwargs": os.getenv(
            "OAUTH_CLIENT_KWARGS", {"scope": f"openid email {oauth_role_uri}"}
        ),
    }
    oauth = OAuth()
    filtered_settings = {k: v for k, v in oauth_settings.items() if v is not None}
    client = oauth.register(filtered_settings)
    return await client.authorize_redirect(request, redirect_uri)


@requires("authenticated")
async def logout(request: Request):
    """
    logout
    ---
    post:
      summary: Logout
      description: Logout
      responses:
        "302":
          description: Redirect after successful logout
    """
    request.session.pop("user", None)
    return RedirectResponse(url="/")
