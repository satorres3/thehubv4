import msal

from .config import MSAL_CLIENT_ID, MSAL_CLIENT_SECRET, MSAL_TENANT_ID


AUTHORITY = f"https://login.microsoftonline.com/{MSAL_TENANT_ID}"

client_app = msal.ConfidentialClientApplication(
    MSAL_CLIENT_ID,
    authority=AUTHORITY,
    client_credential=MSAL_CLIENT_SECRET,
)

