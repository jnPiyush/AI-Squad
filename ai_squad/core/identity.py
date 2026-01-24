"""Identity dossier helpers for provenance and routing trust."""
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


@dataclass
class IdentityDossier:
    workspace_id: str
    workspace_name: str
    workspace_root: str
    agents: List[str]
    generated_at: str
    author: Optional[str] = None
    commit_sha: Optional[str] = None
    extra: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict:
        payload = asdict(self)
        # Ensure extra is a dict
        payload["extra"] = payload.get("extra") or {}
        return payload


class IdentityManager:
    """Builds and persists identity dossiers."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.identity_dir = self.workspace_root / ".squad" / "identity"
        self.identity_file = self.identity_dir / "identity.json"
        self.identity_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        *,
        workspace_name: str,
        agents: List[str],
        author: Optional[str] = None,
        commit_sha: Optional[str] = None,
        extra: Optional[Dict[str, str]] = None,
    ) -> IdentityDossier:
        dossier = IdentityDossier(
            workspace_id=str(uuid.uuid4()),
            workspace_name=workspace_name,
            workspace_root=str(self.workspace_root),
            agents=sorted(set(agents)),
            generated_at=datetime.now().isoformat(),
            author=author,
            commit_sha=commit_sha,
            extra=extra or {},
        )
        logger.info("identity_dossier_built", extra={"identity": dossier.to_dict()})
        return dossier

    def save(self, dossier: IdentityDossier) -> Path:
        self.identity_dir.mkdir(parents=True, exist_ok=True)
        self.identity_file.write_text(json.dumps(dossier.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
        logger.info("identity_dossier_saved", extra={"path": str(self.identity_file)})
        return self.identity_file

    def load(self) -> Optional[IdentityDossier]:
        if not self.identity_file.exists():
            return None
        try:
            data = json.loads(self.identity_file.read_text(encoding="utf-8"))
            return IdentityDossier(**data)
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
            logger.warning("Failed to load identity dossier: %s", exc)
            return None
