from http.cookies import SimpleCookie
from azure.functions import HttpRequest
from typing import Optional


def get_cookie(req: HttpRequest, name: str) -> Optional[str]:
    raw = req.headers.get("Cookie", "")
    jar = SimpleCookie()
    jar.load(raw)
    return jar[name].value if name in jar else None

