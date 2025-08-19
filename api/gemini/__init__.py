"""Gemini API proxy endpoint.

This Azure Function proxies requests from the frontend to the Google
Generative Language API.  It supports both standard JSON responses and
streaming responses encoded as NDJSON.  Knowledge base files stored on the
server are attached to the request as inline data before forwarding to
Gemini.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

import httpx
from azure.functions import HttpRequest, HttpResponse

from ..shared.config import GEMINI_API_KEY


GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"


def _load_knowledge_parts(container_id: str) -> List[Dict[str, object]]:
    """Load knowledge files for *container_id* and return inlineData parts."""

    parts: List[Dict[str, object]] = []
    knowledge_dir = KNOWLEDGE_ROOT / container_id
    if not knowledge_dir.exists():
        return parts

    for file in knowledge_dir.iterdir():
        if not file.is_file():
            continue
        mime_type, _ = mimetypes.guess_type(file.name)
        if not mime_type:
            mime_type = "application/octet-stream"
        data = base64.b64encode(file.read_bytes()).decode()
        parts.append({"inlineData": {"mimeType": mime_type, "data": data}})

    return parts


async def _stream_gemini(url: str, payload: Dict[str, object]) -> AsyncIterator[bytes]:
    """Stream response from Gemini and yield NDJSON encoded bytes."""

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json=payload) as resp:
            async for line in resp.aiter_lines():
                if line:
                    # Ensure each line ends with a newline so the client can parse NDJSON
                    yield (line + "\n").encode()


async def main(req: HttpRequest) -> HttpResponse:
    if not GEMINI_API_KEY:
        return HttpResponse("Gemini API key not configured", status_code=500)

    try:
        body = req.get_json()
    except ValueError:
        return HttpResponse("Invalid JSON body", status_code=400)

    stream: bool = bool(body.get("stream"))
    params: Dict[str, object] = body.get("params", {})

    # Extract containerId for knowledge lookup but do not forward to Gemini
    container_id: Optional[str] = params.pop("containerId", None)

    contents = params.get("contents")
    if isinstance(contents, dict):
        user_parts: List[Dict[str, object]] = contents.get("parts", [])
        if container_id:
            knowledge_parts = _load_knowledge_parts(container_id)
            if knowledge_parts:
                user_parts = knowledge_parts + user_parts
        params["contents"] = [{"role": "user", "parts": user_parts}]

    model = params.get("model")
    if not model:
        return HttpResponse("Missing model parameter", status_code=400)

    if stream:
        url = f"{GEMINI_API_ROOT}/{model}:streamGenerateContent?key={GEMINI_API_KEY}"
        stream_iter = _stream_gemini(url, params)
        return HttpResponse(stream_iter, mimetype="application/x-ndjson", status_code=200)

    url = f"{GEMINI_API_ROOT}/{model}:generateContent?key={GEMINI_API_KEY}"
    async with httpx.AsyncClient(timeout=None) as client:
        resp = await client.post(url, json=params)

    return HttpResponse(resp.text, status_code=resp.status_code, mimetype="application/json")

