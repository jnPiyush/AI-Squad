"""
Hook Management

Hook persistence for AI-Squad work items.
Hooks provide durable storage and optional git worktrees for each work item.
"""
import json
import logging
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .workstate import WorkItem

logger = logging.getLogger(__name__)


class HookManager:
    """Manage hook persistence for work items."""

    def __init__(
        self,
        workspace_root: Path,
        hooks_dir: Optional[str] = None,
        use_git_worktree: bool = False,
    ):
        self.workspace_root = workspace_root
        self.hooks_dir = workspace_root / (hooks_dir or ".squad/hooks")
        self.use_git_worktree = use_git_worktree

    def ensure_hook(self, item: "WorkItem") -> Path:
        """Ensure a hook exists for the work item and write metadata."""
        hook_path = self._hook_path(item.id)
        hook_path.mkdir(parents=True, exist_ok=True)

        if self.use_git_worktree:
            self._ensure_worktree(hook_path)

        self.write_metadata(item)
        return hook_path

    def write_metadata(self, item: "WorkItem") -> None:
        """Write work item metadata into the hook directory."""
        hook_path = self._hook_path(item.id)
        hook_path.mkdir(parents=True, exist_ok=True)

        payload = asdict(item)
        payload["status"] = item.status.value
        payload["updated_at"] = datetime.now().isoformat()

        metadata_file = hook_path / "work_item.json"
        metadata_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def remove_hook(self, item_id: str) -> None:
        """Remove hook metadata without deleting the worktree contents."""
        hook_path = self._hook_path(item_id)
        metadata_file = hook_path / "work_item.json"
        if metadata_file.exists():
            metadata_file.unlink()

    def list_hooks(self) -> List[str]:
        """List hook directories."""
        if not self.hooks_dir.exists():
            return []
        return [p.name for p in self.hooks_dir.iterdir() if p.is_dir()]

    def _hook_path(self, item_id: str) -> Path:
        return self.hooks_dir / item_id

    def _ensure_worktree(self, hook_path: Path) -> None:
        """Attach a git worktree to the hook directory if possible."""
        git_dir = self.workspace_root / ".git"
        if not git_dir.exists():
            return

        if (hook_path / ".git").exists():
            return

        try:
            subprocess.run(
                ["git", "worktree", "add", str(hook_path), "HEAD"],
                cwd=self.workspace_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
            logger.warning("Hook worktree creation failed: %s", exc)
