from azure.functions import HttpRequest, HttpResponse
import msal

from shared.config import MSAL_CLIENT_ID, MSAL_CLIENT_SECRET, MSAL_TENANT_ID, APP_URI
from shared.session import encrypt_session


AUTHORITY = f"https://login.microsoftonline.com/{MSAL_TENANT_ID}"


def _build_redirect_uri(req: HttpRequest) -> str:
    base = APP_URI.rstrip("/") if APP_URI else req.url.split("/api/")[0]
    return f"{base}/api/auth/callback"


def main(req: HttpRequest) -> HttpResponse:
    code = req.params.get("code")
    verifier = req.cookies.get("verifier")
    if not code or not verifier:
        return HttpResponse("Missing authentication parameters.", status_code=400)

    cache = msal.SerializableTokenCache()
    app = msal.ConfidentialClientApplication(
        MSAL_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=MSAL_CLIENT_SECRET,
        token_cache=cache,
    )

    result = app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=_build_redirect_uri(req),
        code_verifier=verifier,
    )

    if "error" in result:
        description = result.get("error_description", "Authentication failed")
        return HttpResponse(description, status_code=400)

    accounts = app.get_accounts()
    account = accounts[0] if accounts else None

    session_token = encrypt_session(
        {
            "token_cache": cache.serialize(),
            "home_account_id": account.get("home_account_id") if account else None,
        }
    )

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Set-Cookie": (
            f"session={session_token}; Path=/; HttpOnly; SameSite=None; Secure"
        ),
    }
    body = "<html><body><script>window.location.replace('/');</script></body></html>"
    return HttpResponse(body=body, status_code=200, headers=headers, mimetype="text/html")
