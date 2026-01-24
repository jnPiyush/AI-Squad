"""Capability registry for skills/workflows across scopes.

Supports install/upgrade/list with checksum verification.
"""
from dataclasses import dataclass, field
import json
import logging
import shutil
import tarfile
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import hmac
import yaml

logger = logging.getLogger(__name__)


@dataclass
class CapabilityPackage:
    """Represents a capability package manifest."""

    name: str
    version: str
    scope: str  # public|org|project
    capability_tags: List[str] = field(default_factory=list)
    checksum_sha256: Optional[str] = None
    signature: Optional[str] = None
    description: Optional[str] = None
    source_path: Optional[Path] = None

    @classmethod
    def from_manifest(cls, manifest: Dict, source_path: Path) -> "CapabilityPackage":
        required = ["name", "version", "scope"]
        for key in required:
            if key not in manifest:
                raise ValueError(f"Manifest missing required field '{key}'")

        return cls(
            name=str(manifest["name"]),
            version=str(manifest["version"]),
            scope=str(manifest["scope"]),
            capability_tags=list(manifest.get("capability_tags", [])),
            checksum_sha256=manifest.get("checksum_sha256"),
            signature=manifest.get("signature"),
            description=manifest.get("description"),
            source_path=source_path,
        )

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "scope": self.scope,
            "capability_tags": self.capability_tags,
            "checksum_sha256": self.checksum_sha256,
            "signature": self.signature,
            "description": self.description,
        }


class CapabilityRegistry:
    """Registry for installed capability packages."""

    MANIFEST_FILES = ["capability.yaml", "capability.yml", "capability.json"]

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.registry_dir = self.workspace_root / ".squad" / "capabilities"
        self.installed_file = self.registry_dir / "installed.json"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self._installed: Dict[str, CapabilityPackage] = {}
        self._load_installed()

    def install(self, package_path: Path) -> CapabilityPackage:
        """Install or upgrade a capability package from directory or tarball."""

        package_path = package_path.resolve()
        if not package_path.exists():
            raise FileNotFoundError(f"Package not found: {package_path}")

        temp_dir = None
        source_dir = package_path
        if package_path.is_file():
            temp_dir = self.registry_dir / f"tmp-{package_path.stem}"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True)
            with tarfile.open(package_path, "r:gz") as tar:
                tar.extractall(temp_dir, filter="data")
            source_dir = temp_dir

        manifest_path = self._find_manifest(source_dir)
        manifest_data = self._load_manifest(manifest_path)
        pkg = CapabilityPackage.from_manifest(manifest_data, manifest_path)

        computed_checksum = self._compute_dir_checksum(source_dir)
        if pkg.checksum_sha256 and pkg.checksum_sha256 != computed_checksum:
            raise ValueError(
                f"Checksum mismatch for {pkg.name}: expected {pkg.checksum_sha256}, got {computed_checksum}"
            )
        pkg.checksum_sha256 = pkg.checksum_sha256 or computed_checksum

        if pkg.signature:
            secret = (Path.cwd() / ".squad" / "capabilities" / "signature.key")
            key = None
            if secret.exists():
                key = secret.read_text(encoding="utf-8").strip()
            if not key:
                raise ValueError("Capability signature provided but no signature key found")

            expected = hmac.new(key.encode("utf-8"), computed_checksum.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, pkg.signature):
                raise ValueError(f"Signature verification failed for {pkg.name}")

        target_dir = self.registry_dir / f"{pkg.name}-{pkg.version}"
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)

        # Update installed registry
        self._installed[pkg.name] = pkg
        self._save_installed()

        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir)

        logger.info("capability_installed", extra={"capability": pkg.to_dict()})
        return pkg

    def list(self) -> List[CapabilityPackage]:
        """List installed capability packages."""
        return list(self._installed.values())

    def get(self, name: str) -> Optional[CapabilityPackage]:
        return self._installed.get(name)

    # Internal helpers
    def _find_manifest(self, source_dir: Path) -> Path:
        for filename in self.MANIFEST_FILES:
            candidate = source_dir / filename
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"No manifest found in {source_dir}")

    def _load_manifest(self, path: Path) -> Dict:
        if path.suffix in {".yaml", ".yml"}:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_installed(self) -> None:
        payload = {name: pkg.to_dict() for name, pkg in self._installed.items()}
        self.installed_file.parent.mkdir(parents=True, exist_ok=True)
        self.installed_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _load_installed(self) -> None:
        if not self.installed_file.exists():
            return
        try:
            data = json.loads(self.installed_file.read_text(encoding="utf-8"))
            for name, meta in data.items():
                self._installed[name] = CapabilityPackage.from_manifest(meta, self.installed_file)
        except json.JSONDecodeError:
            logger.warning("Installed capabilities file corrupted; resetting")
            self._installed = {}

    @staticmethod
    def _compute_dir_checksum(root: Path) -> str:
        """Compute deterministic sha256 over files, ignoring checksum field in manifest."""

        digest = hashlib.sha256()
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            if path.name in CapabilityRegistry.MANIFEST_FILES:
                # Ignore checksum field inside manifest to avoid circularity
                digest.update(CapabilityRegistry._manifest_bytes_without_checksum(path))
            else:
                digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _manifest_bytes_without_checksum(path: Path) -> bytes:
        if path.suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.pop("checksum_sha256", None)
            return yaml.safe_dump(data, sort_keys=True).encode("utf-8")
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.pop("checksum_sha256", None)
            return json.dumps(data, sort_keys=True).encode("utf-8")
        return path.read_bytes()
