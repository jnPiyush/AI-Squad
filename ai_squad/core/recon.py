"""
Reconnaissance summary for situation awareness.
"""
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ai_squad.core.runtime_paths import resolve_runtime_dir

from ai_squad.core.router import HealthConfig, HealthView
from ai_squad.core.signal import SignalManager
from ai_squad.core.workstate import WorkStateManager

logger = logging.getLogger(__name__)


@dataclass
class ReconSummary:
    timestamp: str
    work_state: Dict[str, Any]
    signal: Dict[str, Any]
    routing: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "work_state": self.work_state,
            "signal": self.signal,
            "routing": self.routing,
        }


class ReconManager:
    """Builds and stores reconnaissance summaries."""

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        workstate_manager: Optional[WorkStateManager] = None,
        signal_manager: Optional[SignalManager] = None,
        routing_config: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        base_dir: Optional[str] = None,
    ) -> None:
        self.workspace_root = workspace_root or Path.cwd()
        self.workstate_manager = workstate_manager or WorkStateManager(self.workspace_root, config=config)
        self.signal_manager = signal_manager or SignalManager(self.workspace_root, config=config, base_dir=base_dir)
        self.routing_config = routing_config or {}
        runtime_dir = resolve_runtime_dir(self.workspace_root, config=config, base_dir=base_dir)
        self.recon_dir = runtime_dir / "recon"

    def build_summary(self) -> ReconSummary:
        health_cfg = HealthConfig(
            warn_block_rate=self.routing_config.get("warn_block_rate", 0.25),
            critical_block_rate=self.routing_config.get("critical_block_rate", 0.5),
            circuit_breaker_block_rate=self.routing_config.get("circuit_breaker_block_rate", 0.7),
            throttle_block_rate=self.routing_config.get("throttle_block_rate", 0.5),
            min_events=self.routing_config.get("min_events", 5),
            window=self.routing_config.get("window", 200),
        )
        health_view = HealthView(workspace_root=self.workspace_root, window=health_cfg.window)
        routing_summary = health_view.summarize(health_cfg)

        return ReconSummary(
            timestamp=datetime.now().isoformat(),
            work_state=self.workstate_manager.get_stats(),
            signal=self.signal_manager.get_stats(),
            routing=routing_summary,
        )

    def save_summary(self, summary: Optional[ReconSummary] = None) -> Path:
        summary = summary or self.build_summary()
        self.recon_dir.mkdir(parents=True, exist_ok=True)
        path = self.recon_dir / "recon-summary.json"
        path.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
        logger.info("Recon summary saved to %s", path)
        return path
