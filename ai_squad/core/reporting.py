"""
After-operation reporting utilities.
"""
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_squad.core.runtime_paths import resolve_runtime_dir

from ai_squad.core.convoy import Convoy

logger = logging.getLogger(__name__)


@dataclass
class AfterOperationReport:
    convoy_id: str
    name: str
    status: str
    completed: int
    failed: int
    errors: List[str]
    created_at: str

    def to_markdown(self) -> str:
        lines = [
            f"# After-Operation Report: {self.name}",
            "",
            f"- Convoy ID: {self.convoy_id}",
            f"- Status: {self.status}",
            f"- Completed: {self.completed}",
            f"- Failed: {self.failed}",
            f"- Created: {self.created_at}",
            "",
        ]
        if self.errors:
            lines.append("## Errors")
            for err in self.errors:
                lines.append(f"- {err}")
        return "\n".join(lines)


class ReportManager:
    """Generates and stores after-operation reports."""

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        base_dir: Optional[str] = None,
    ) -> None:
        self.workspace_root = workspace_root or Path.cwd()
        if reports_dir is not None:
            self.reports_dir = reports_dir
        else:
            runtime_dir = resolve_runtime_dir(self.workspace_root, config=config, base_dir=base_dir)
            self.reports_dir = runtime_dir / "reports"

    def write_convoy_report(self, convoy: Convoy) -> Path:
        progress = convoy.get_progress()
        report = AfterOperationReport(
            convoy_id=convoy.id,
            name=convoy.name,
            status=convoy.status.value,
            completed=progress.get("completed", 0),
            failed=progress.get("failed", 0),
            errors=convoy.errors,
            created_at=datetime.now().isoformat(),
        )
        return self._write_report(report)

    def write_direct_report(self, convoy_id: str, results: Dict[str, Any]) -> Path:
        report = AfterOperationReport(
            convoy_id=convoy_id,
            name=convoy_id,
            status="completed" if results.get("failed", 0) == 0 else "partial",
            completed=results.get("completed", 0),
            failed=results.get("failed", 0),
            errors=results.get("errors", []),
            created_at=datetime.now().isoformat(),
        )
        return self._write_report(report)

    def _write_report(self, report: AfterOperationReport) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        path = self.reports_dir / f"after-operation-{report.convoy_id}.md"
        path.write_text(report.to_markdown(), encoding="utf-8")
        logger.info("After-operation report saved to %s", path)
        return path
