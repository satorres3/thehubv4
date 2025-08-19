import json
import os

from azure.functions import HttpRequest, HttpResponse


def main(req: HttpRequest) -> HttpResponse:
    """Return public configuration flags for auth providers."""
    ms_required = ["MSAL_CLIENT_ID", "MSAL_TENANT_ID", "MSAL_CLIENT_SECRET"]
    google_required = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]

    is_ms_configured = all(os.getenv(var) for var in ms_required)
    is_google_configured = all(os.getenv(var) for var in google_required)

    body = json.dumps(
        {
            "auth": {
                "isMicrosoftConfigured": is_ms_configured,
                "isGoogleConfigured": is_google_configured,
            }
        }
    )

    return HttpResponse(body, mimetype="application/json")
