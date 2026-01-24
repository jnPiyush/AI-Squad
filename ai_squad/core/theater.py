"""
Theater registry for multi-sector coordination.

Stores theater/sector metadata and routing table in .squad/theater.json.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Sector:
    """Represents a sector (workspace/repo)."""
    name: str
    repo_path: str
    staging_path: str


@dataclass
class Theater:
    """Represents a theater with sectors and routing rules."""
    name: str
    sectors: Dict[str, Sector] = field(default_factory=dict)
    routing: Dict[str, str] = field(default_factory=dict)  # prefix -> sector name


class TheaterRegistry:
    """Persistent registry for theaters and sectors."""

    FILE_NAME = "theater.json"

    def __init__(self, workspace_root: Optional[Path] = None, config: Optional[Dict] = None) -> None:
        self.workspace_root = workspace_root or Path.cwd()
        self.squad_dir = self.workspace_root / ".squad"
        self.registry_file = self.squad_dir / self.FILE_NAME
        self.config = config or {}
        self._theaters: Dict[str, Theater] = {}
        self._load()

        if not self._theaters:
            default_name = self.config.get("theater", {}).get("default", "default")
            self._theaters[default_name] = Theater(name=default_name)
            self._save()

    def list_theaters(self) -> List[Theater]:
        return list(self._theaters.values())

    def get_theater(self, name: str) -> Optional[Theater]:
        return self._theaters.get(name)

    def upsert_theater(self, name: str) -> Theater:
        theater = self._theaters.get(name)
        if not theater:
            theater = Theater(name=name)
            self._theaters[name] = theater
            self._save()
        return theater

    def add_sector(self, theater_name: str, sector_name: str, repo_path: str, staging_path: Optional[str] = None) -> Sector:
        theater = self.upsert_theater(theater_name)
        staging_path = staging_path or str(self.squad_dir / "staging" / sector_name)
        sector = Sector(name=sector_name, repo_path=repo_path, staging_path=staging_path)
        theater.sectors[sector_name] = sector
        self._save()
        return sector

    def set_route(self, theater_name: str, prefix: str, sector_name: str) -> None:
        theater = self.upsert_theater(theater_name)
        if sector_name not in theater.sectors:
            raise ValueError(f"Sector not found: {sector_name}")
        theater.routing[prefix] = sector_name
        self._save()

    def resolve_sector(self, prefix: str, theater_name: Optional[str] = None) -> Optional[Sector]:
        theater = self._get_default_theater(theater_name)
        if not theater:
            return None
        sector_name = theater.routing.get(prefix)
        if not sector_name:
            return None
        return theater.sectors.get(sector_name)

    def ensure_staging_areas(self, theater_name: Optional[str] = None) -> List[Path]:
        theater = self._get_default_theater(theater_name)
        if not theater:
            return []
        created: List[Path] = []
        for sector in theater.sectors.values():
            path = Path(sector.staging_path)
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)
        return created

    def _get_default_theater(self, name: Optional[str]) -> Optional[Theater]:
        if name:
            return self._theaters.get(name)
        default_name = self.config.get("theater", {}).get("default", "default")
        return self._theaters.get(default_name)

    def _load(self) -> None:
        if not self.registry_file.exists():
            return
        try:
            data = json.loads(self.registry_file.read_text(encoding="utf-8"))
            theaters: Dict[str, Theater] = {}
            for name, tdata in data.get("theaters", {}).items():
                sectors = {
                    sname: Sector(**sdata)
                    for sname, sdata in tdata.get("sectors", {}).items()
                }
                theaters[name] = Theater(
                    name=name,
                    sectors=sectors,
                    routing=tdata.get("routing", {}),
                )
            self._theaters = theaters
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.error("Failed to load theater registry: %s", exc)
            self._theaters = {}

    def _save(self) -> None:
        self.squad_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "theaters": {
                name: {
                    "sectors": {sname: asdict(sector) for sname, sector in theater.sectors.items()},
                    "routing": theater.routing,
                }
                for name, theater in self._theaters.items()
            },
        }
        self.registry_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
