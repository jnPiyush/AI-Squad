"""Lightweight non-LLM scout workers with checkpoints."""
from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ScoutTask:
    name: str
    status: str = "pending"  # pending|running|completed|failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScoutRun:
    run_id: str
    tasks: List[ScoutTask] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoutRun":
        tasks = [ScoutTask(**t) for t in data.get("tasks", [])]
        return cls(
            run_id=data.get("run_id", ""),
            tasks=tasks,
            created_at=data.get("created_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at"),
            metadata=data.get("metadata", {}),
        )


class ScoutWorker:
    """Executes deterministic, non-LLM tasks with checkpoints."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.scout_dir = self.workspace_root / ".squad" / "scout_workers"
        self.scout_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        tasks: Dict[str, Callable[[], Any]],
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScoutRun:
        run = ScoutRun(
            run_id=f"scout-{uuid.uuid4().hex[:8]}",
            metadata=metadata or {},
        )

        for name, func in tasks.items():
            task = self._run_task(name, func)
            run.tasks.append(task)
            self._checkpoint(run)

        run.completed_at = datetime.now().isoformat()
        self._checkpoint(run)
        logger.info("scout_run_completed", extra={"run_id": run.run_id})
        return run

    def _run_task(self, name: str, func: Callable[[], Any]) -> ScoutTask:
        task = ScoutTask(
            name=name,
            status="running",
            started_at=datetime.now().isoformat(),
        )
        try:
            result = func()
            task.result = result
            task.status = "completed"
        except (RuntimeError, ValueError, TypeError) as exc:
            task.error = str(exc)
            task.status = "failed"
            logger.error(
                "scout_task_failed",
                extra={"task": name, "error": str(exc)},
            )

        task.completed_at = datetime.now().isoformat()
        return task

    def _checkpoint(self, run: ScoutRun) -> None:
        checkpoint_file = self.scout_dir / f"{run.run_id}.json"
        checkpoint_file.write_text(json.dumps(run.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
        logger.debug("scout_checkpoint_saved", extra={"run_id": run.run_id, "path": str(checkpoint_file)})

    def list_runs(self) -> List[str]:
        """List scout run IDs available on disk."""
        runs = [p.stem for p in self.scout_dir.glob("scout-*.json")]
        return sorted(runs)

    def load_run(self, run_id: str) -> Optional[ScoutRun]:
        """Load a scout run by ID."""
        run_file = self.scout_dir / f"{run_id}.json"
        if not run_file.exists():
            return None
        try:
            data = json.loads(run_file.read_text(encoding="utf-8"))
            return ScoutRun.from_dict(data)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("Failed to load scout run %s: %s", run_id, e)
            return None