from __future__ import annotations

import json
from azure.functions import HttpRequest, HttpResponse

from ..shared.knowledge_store import list_knowledge_files


def main(req: HttpRequest) -> HttpResponse:
    """Return metadata for all knowledge files in a container."""

    container_id = req.params.get("containerId")
    if not container_id:
        try:
            body = req.get_json()
            container_id = body.get("containerId")
        except ValueError:
            container_id = None
    if not container_id:
        return HttpResponse("Missing containerId", status_code=400)

    files = list_knowledge_files(container_id)
    return HttpResponse(json.dumps(files), mimetype="application/json", status_code=200)
