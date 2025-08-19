from __future__ import annotations

import json
from pathlib import Path
from azure.functions import HttpRequest, HttpResponse

from ..shared.knowledge_store import delete_knowledge_file, list_knowledge_files

KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"


def main(req: HttpRequest) -> HttpResponse:
    """Delete a knowledge base file."""

    try:
        body = req.get_json()
    except ValueError:
        return HttpResponse("Invalid JSON body", status_code=400)

    container_id = body.get("containerId")
    file_id = body.get("fileId")
    if not container_id or not file_id:
        return HttpResponse("Missing containerId or fileId", status_code=400)

    files = list_knowledge_files(container_id)
    file_meta = next((f for f in files if f["id"] == file_id), None)
    if not file_meta:
        return HttpResponse("File not found", status_code=404)

    delete_knowledge_file(container_id, file_id)

    ext = Path(file_meta["name"]).suffix
    file_path = KNOWLEDGE_ROOT / container_id / f"{file_id}{ext}"
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    return HttpResponse(status_code=200)
