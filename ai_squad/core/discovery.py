"""Remote discovery with privacy defaults and filters."""
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_squad.core.runtime_paths import resolve_runtime_dir
import uuid

logger = logging.getLogger(__name__)


@dataclass
class RemoteEntry:
    id: str
    url: str
    scopes: List[str]
    visibility: str  # private|org|public
    tags: List[str]
    status: str = "unknown"
    added_at: str = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "scopes": self.scopes,
            "visibility": self.visibility,
            "tags": self.tags,
            "status": self.status,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemoteEntry":
        return cls(**data)


class DiscoveryIndex:
    """Stores remote discovery metadata with privacy defaults."""

    def __init__(self, workspace_root: Optional[Path] = None, config: Optional[Dict[str, Any]] = None, base_dir: Optional[str] = None):
        self.workspace_root = workspace_root or Path.cwd()
        runtime_dir = resolve_runtime_dir(self.workspace_root, config=config, base_dir=base_dir)
        self.discovery_file = runtime_dir / "discovery.json"
        self.discovery_file.parent.mkdir(parents=True, exist_ok=True)
        self._remotes: Dict[str, RemoteEntry] = {}
        self._load()

    def add_remote(self, url: str, *, scopes: Optional[List[str]] = None, visibility: str = "private", tags: Optional[List[str]] = None, status: str = "unknown") -> RemoteEntry:
        scopes = scopes or []
        tags = tags or []
        remote_id = f"remote-{uuid.uuid4().hex[:8]}"
        entry = RemoteEntry(id=remote_id, url=url, scopes=scopes, visibility=visibility, tags=tags, status=status)
        self._remotes[remote_id] = entry
        self._save()
        logger.info("remote_added", extra={"remote": entry.to_dict()})
        return entry

    def query(self, *, scope: Optional[str] = None, visibility: Optional[str] = None, tag: Optional[str] = None) -> List[RemoteEntry]:
        results = list(self._remotes.values())
        if scope:
            results = [r for r in results if scope in r.scopes]
        if visibility:
            results = [r for r in results if r.visibility == visibility]
        if tag:
            results = [r for r in results if tag in r.tags]
        return results

    def list(self) -> List[RemoteEntry]:
        return list(self._remotes.values())

    def _save(self) -> None:
        payload = {rid: r.to_dict() for rid, r in self._remotes.items()}
        self.discovery_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self.discovery_file.exists():
            return
        try:
            data = json.loads(self.discovery_file.read_text(encoding="utf-8"))
            self._remotes = {rid: RemoteEntry.from_dict(meta) for rid, meta in data.items()}
        except json.JSONDecodeError:
            logger.warning("Discovery index corrupted; resetting")
            self._remotes = {}
