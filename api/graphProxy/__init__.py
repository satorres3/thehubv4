"""Microsoft Graph proxy endpoint.

This Azure Function acquires an access token on behalf of the user using
MSAL, forwards the incoming request to the Microsoft Graph API and streams
the response back to the caller.  If re-authentication is required the
function responds with ``401 Unauthorized`` so the client can initiate the
sign-in flow again.
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

import httpx
import msal
from azure.functions import HttpRequest, HttpResponse

from ..shared.config import MSAL_CLIENT_ID, MSAL_CLIENT_SECRET, MSAL_TENANT_ID
from ..shared.session import decrypt_session
from ..shared.cookies import get_cookie


AUTHORITY = f"https://login.microsoftonline.com/{MSAL_TENANT_ID}"
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


async def _stream_response(resp: httpx.Response) -> AsyncIterator[bytes]:
    """Yield response body chunks for streaming back to the client."""

    async for chunk in resp.aiter_bytes():
        if chunk:
            yield chunk


async def main(req: HttpRequest) -> HttpResponse:
    path = req.params.get("path")
    if not path:
        return HttpResponse("Missing Graph path", status_code=400)

    session_token: Optional[str] = get_cookie(req, "session")
    if not session_token:
        return HttpResponse("Unauthorized", status_code=401)

    try:
        session = decrypt_session(session_token)
    except Exception:
        return HttpResponse("Invalid session", status_code=401)

    cache = msal.SerializableTokenCache()
    serialized_cache = session.get("token_cache")
    if serialized_cache:
        cache.deserialize(serialized_cache)

    app = msal.ConfidentialClientApplication(
        MSAL_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=MSAL_CLIENT_SECRET,
        token_cache=cache,
    )

    account = None
    home_account_id = session.get("home_account_id")
    if home_account_id:
        accounts = app.get_accounts(home_account_id=home_account_id)
        if accounts:
            account = accounts[0]

    result = app.acquire_token_silent(
        ["https://graph.microsoft.com/.default"], account=account
    )

    if not result or "access_token" not in result:
        # Token could not be acquired silently; user interaction required
        return HttpResponse("Authentication required", status_code=401)

    access_token = result["access_token"]
    url = f"{GRAPH_ROOT}{path}"

    headers = {"Authorization": f"Bearer {access_token}"}
    content_type = req.headers.get("content-type")
    if content_type:
        headers["Content-Type"] = content_type

    data = req.get_body() if req.get_body() else None

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            req.method,
            url,
            headers=headers,
            content=data,
        ) as resp:
            stream = _stream_response(resp)
            return HttpResponse(
                stream,
                status_code=resp.status_code,
                mimetype=resp.headers.get("content-type"),
            )

