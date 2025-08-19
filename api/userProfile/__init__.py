from __future__ import annotations

import base64
import json
from typing import Optional

import httpx
import msal
from azure.functions import HttpRequest, HttpResponse

from ..shared.config import MSAL_CLIENT_ID, MSAL_CLIENT_SECRET, MSAL_TENANT_ID
from ..shared.session import decrypt_session
from ..shared.cookies import get_cookie

AUTHORITY = f"https://login.microsoftonline.com/{MSAL_TENANT_ID}"
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


async def main(req: HttpRequest) -> HttpResponse:
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

    result = app.acquire_token_silent(["User.Read"], account=account)
    if not result or "access_token" not in result:
        return HttpResponse("Authentication required", status_code=401)

    access_token = result["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(f"{GRAPH_ROOT}/me", headers=headers)
        if profile_resp.status_code != 200:
            return HttpResponse("Failed to fetch profile", status_code=profile_resp.status_code)
        profile = profile_resp.json()

        photo_resp = await client.get(f"{GRAPH_ROOT}/me/photo/$value", headers=headers)
        avatar_url = ""
        if photo_resp.status_code == 200:
            mime = photo_resp.headers.get("content-type", "image/jpeg")
            b64 = base64.b64encode(photo_resp.content).decode()
            avatar_url = f"data:{mime};base64,{b64}"

    user = {
        "firstName": profile.get("givenName", ""),
        "lastName": profile.get("surname", ""),
        "email": profile.get("mail") or profile.get("userPrincipalName", ""),
        "avatarUrl": avatar_url,
    }

    body = json.dumps(user)
    return HttpResponse(body, mimetype="application/json")
