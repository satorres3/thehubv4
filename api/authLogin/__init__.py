import base64
import hashlib
import secrets

from azure.functions import HttpRequest, HttpResponse

from shared.config import MSAL_CLIENT_ID, MSAL_CLIENT_SECRET, MSAL_TENANT_ID, APP_URI
from msal import ConfidentialClientApplication


AUTHORITY = f"https://login.microsoftonline.com/{MSAL_TENANT_ID}"


def _build_redirect_uri(req: HttpRequest) -> str:
    base = APP_URI.rstrip("/") if APP_URI else req.url.split("/api/")[0]
    return f"{base}/api/auth/callback"


def main(req: HttpRequest) -> HttpResponse:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )

    client = ConfidentialClientApplication(
        MSAL_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=MSAL_CLIENT_SECRET,
    )

    authorization_url = client.get_authorization_request_url(
        ["User.Read"],
        redirect_uri=_build_redirect_uri(req),
        code_challenge=challenge,
        code_challenge_method="S256",
    )

    headers = {
        "Location": authorization_url,
        "Set-Cookie": (
            f"verifier={verifier}; Path=/; HttpOnly; SameSite=None; Secure; Max-Age=600"
        ),
    }
    return HttpResponse(status_code=302, headers=headers)
