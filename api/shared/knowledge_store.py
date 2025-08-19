from __future__ import annotations

"""In-memory knowledge base store.

This module mirrors the behavior of the former TypeScript implementation
(api/src/shared/knowledge.ts).  It keeps metadata for knowledge files in
memory and stores the base64-encoded file contents separately.  The data
is **not** persistent and will be lost when the process restarts.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeFile:
    """Metadata describing an uploaded knowledge base file."""

    id: str
    name: str
    type: str
    size: int
    uploadDate: str


@dataclass
class Container:
    """Container holding a list of knowledge files."""

    id: str
    knowledgeBase: List[KnowledgeFile]


@dataclass
class AppStatePayload:
    containers: List[Container]
    branding: Dict[str, Any]
    availableModels: List[Any]


# Global in-memory state
app_state: Optional[AppStatePayload] = None
knowledge_files_content: Dict[str, str] = {}


def _ensure_state_loaded() -> None:
    """Lazy-initialize the in-memory state."""

    global app_state, knowledge_files_content
    if app_state is not None:
        return

    logging.info("Initializing in-memory backend state for the first time.")
    app_state = AppStatePayload(containers=[], branding={}, availableModels=[])
    knowledge_files_content = {}


def _get_container(container_id: str) -> Optional[Container]:
    _ensure_state_loaded()
    return next((c for c in app_state.containers if c.id == container_id), None)


def list_knowledge_files(container_id: str) -> List[Dict[str, Any]]:
    """Return metadata for all knowledge files of *container_id*."""

    container = _get_container(container_id)
    if not container:
        return []
    return [asdict(f) for f in container.knowledgeBase]


def add_knowledge_file(container_id: str, file_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a file to the knowledge base of *container_id*.

    *file_data* must contain ``name``, ``type``, ``size`` and
    ``base64Content`` fields.
    """

    container = _get_container(container_id)
    if container is None:
        raise ValueError(f"Container with ID {container_id} not found.")

    new_file = KnowledgeFile(
        id=f"file-{int(datetime.utcnow().timestamp()*1000)}-{uuid.uuid4().hex[:8]}",
        name=file_data["name"],
        type=file_data["type"],
        size=int(file_data["size"]),
        uploadDate=datetime.utcnow().isoformat(),
    )

    container.knowledgeBase.append(new_file)
    knowledge_files_content[new_file.id] = file_data.get("base64Content", "")
    return asdict(new_file)


def delete_knowledge_file(container_id: str, file_id: str) -> None:
    """Remove a file from the knowledge base."""

    container = _get_container(container_id)
    if container:
        container.knowledgeBase = [f for f in container.knowledgeBase if f.id != file_id]
    knowledge_files_content.pop(file_id, None)


def get_knowledge_files_with_content(container_id: str) -> List[Dict[str, Any]]:
    """Return metadata along with base64 content for all files."""

    container = _get_container(container_id)
    if not container:
        return []
    return [
        {**asdict(f), "base64Content": knowledge_files_content.get(f.id, "")}
        for f in container.knowledgeBase
    ]


def initialize_state(initial_state: Dict[str, Any]) -> None:
    """Re-initialize the in-memory state using *initial_state* payload."""

    global app_state, knowledge_files_content
    logging.info("Backend in-memory state is being re-initialized.")

    containers: List[Container] = []
    for c in initial_state.get("containers", []):
        kb = [KnowledgeFile(**f) for f in c.get("knowledgeBase", [])]
        containers.append(Container(id=c["id"], knowledgeBase=kb))

    app_state = AppStatePayload(
        containers=containers,
        branding=initial_state.get("branding", {}),
        availableModels=initial_state.get("availableModels", []),
    )
    knowledge_files_content = {}
