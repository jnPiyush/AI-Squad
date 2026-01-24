"""
Worker Lifecycle Management

Tracks ephemeral worker runs for AI-Squad agents.
"""
import json
import logging
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_squad.core.runtime_paths import resolve_runtime_dir

logger = logging.getLogger(__name__)


@dataclass
class WorkerInstance:
    id: str
    agent_type: str
    issue_number: Optional[int] = None
    work_item_id: Optional[str] = None
    status: str = "running"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkerLifecycleManager:
    """Persist worker lifecycle state under .squad/workers.json."""

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        base_dir: Optional[str] = None,
    ):
        self.workspace_root = workspace_root or Path.cwd()
        runtime_dir = resolve_runtime_dir(self.workspace_root, config=config, base_dir=base_dir)
        self.squad_dir = runtime_dir
        self.workers_file = runtime_dir / "workers.json"
        self._ensure_dir()

    def spawn(self, agent_type: str, issue_number: Optional[int] = None, work_item_id: Optional[str] = None) -> WorkerInstance:
        worker = WorkerInstance(
            id=f"worker-{uuid.uuid4().hex[:8]}",
            agent_type=agent_type,
            issue_number=issue_number,
            work_item_id=work_item_id,
        )
        workers = self._load()
        workers[worker.id] = worker
        self._save(workers)
        return worker

    def complete(self, worker_id: str) -> None:
        workers = self._load()
        worker = workers.get(worker_id)
        if not worker:
            return
        worker.status = "completed"
        worker.completed_at = datetime.now().isoformat()
        self._save(workers)

    def fail(self, worker_id: str, error: str) -> None:
        workers = self._load()
        worker = workers.get(worker_id)
        if not worker:
            return
        worker.status = "failed"
        worker.error = error
        worker.completed_at = datetime.now().isoformat()
        self._save(workers)

    def list(self, status: Optional[str] = None) -> List[WorkerInstance]:
        workers = list(self._load().values())
        if status:
            workers = [w for w in workers if w.status == status]
        return workers

    def _ensure_dir(self) -> None:
        self.squad_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, WorkerInstance]:
        if not self.workers_file.exists():
            return {}
        data = json.loads(self.workers_file.read_text(encoding="utf-8"))
        return {k: WorkerInstance(**v) for k, v in data.items()}

    def _save(self, workers: Dict[str, WorkerInstance]) -> None:
        payload = {k: asdict(v) for k, v in workers.items()}
        self.workers_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
