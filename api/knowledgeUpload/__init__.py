from __future__ import annotations

import base64
import json
from pathlib import Path
from azure.functions import HttpRequest, HttpResponse

from ..shared.knowledge_store import add_knowledge_file, delete_knowledge_file

KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"


def main(req: HttpRequest) -> HttpResponse:
    """Upload a knowledge base file and persist it."""

    try:
        body = req.get_json()
    except ValueError:
        return HttpResponse("Invalid JSON body", status_code=400)

    container_id = body.get("containerId")
    file = body.get("file")
    if not container_id or not file:
        return HttpResponse("Missing containerId or file", status_code=400)

    try:
        metadata = add_knowledge_file(container_id, file)
    except ValueError as exc:
        return HttpResponse(str(exc), status_code=404)

    knowledge_dir = KNOWLEDGE_ROOT / container_id
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file["name"]).suffix
    file_path = knowledge_dir / f"{metadata['id']}{ext}"

    try:
        content_bytes = base64.b64decode(file.get("base64Content", ""))
        file_path.write_bytes(content_bytes)
    except Exception as exc:  # pragma: no cover - defensive cleanup
        delete_knowledge_file(container_id, metadata["id"])
        return HttpResponse(f"Failed to save file: {exc}", status_code=500)

    return HttpResponse(json.dumps(metadata), status_code=200, mimetype="application/json")
