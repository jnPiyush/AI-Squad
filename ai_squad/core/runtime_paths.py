"""Runtime path helpers for AI-Squad."""
from pathlib import Path
from typing import Any, Dict, Optional


def resolve_runtime_dir(
    workspace_root: Path,
    config: Optional[Dict[str, Any]] = None,
    base_dir: Optional[str] = None,
) -> Path:
    """Resolve the runtime base directory.

    Priority: explicit base_dir > config.runtime.base_dir > default .squad
    """
    if base_dir:
        return workspace_root / base_dir
    if config and isinstance(config, dict):
        runtime_cfg = config.get("runtime", {})
        base = runtime_cfg.get("base_dir")
        if base:
            return workspace_root / base
    return workspace_root / ".squad"
