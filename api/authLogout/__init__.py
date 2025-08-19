from azure.functions import HttpRequest, HttpResponse
import msal

from shared.config import MSAL_CLIENT_ID, MSAL_CLIENT_SECRET, MSAL_TENANT_ID
from shared.session import decrypt_session


AUTHORITY = f"https://login.microsoftonline.com/{MSAL_TENANT_ID}"


def main(req: HttpRequest) -> HttpResponse:
    session_cookie = req.cookies.get("session")

    if session_cookie:
        try:
            data = decrypt_session(session_cookie)
            cache = msal.SerializableTokenCache()
            cache.deserialize(data.get("token_cache", ""))
            app = msal.ConfidentialClientApplication(
                MSAL_CLIENT_ID,
                authority=AUTHORITY,
                client_credential=MSAL_CLIENT_SECRET,
                token_cache=cache,
            )
            for account in app.get_accounts():
                if account.get("home_account_id") == data.get("home_account_id"):
                    app.remove_account(account)
                    break
        except Exception:
            pass

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Set-Cookie": (
            "session=; Path=/; HttpOnly; SameSite=None; Secure; "
            "Expires=Thu, 01 Jan 1970 00:00:00 GMT"
        ),
    }
    body = "<html><body><script>window.location.replace('/');</script></body></html>"
    return HttpResponse(body=body, status_code=200, headers=headers, mimetype="text/html")
