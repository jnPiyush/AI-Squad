import tarfile
from pathlib import Path

from ai_squad.core.capability_registry import CapabilityRegistry


def make_package(tmp_path: Path, name: str, version: str, checksum: bool = True) -> Path:
    pkg_dir = tmp_path / f"{name}-{version}"
    pkg_dir.mkdir()
    manifest = {
        "name": name,
        "version": version,
        "scope": "project",
        "capability_tags": ["routing", "skills"],
    }
    manifest_path = pkg_dir / "capability.yaml"
    manifest_path.write_text("""
name: {name}
version: {version}
scope: project
capability_tags:
  - routing
  - skills
""".format(name=name, version=version), encoding="utf-8")
    if checksum:
        registry = CapabilityRegistry(tmp_path)
        manifest["checksum_sha256"] = registry.compute_dir_checksum(pkg_dir)
        manifest_path.write_text(
            manifest_path.read_text(encoding="utf-8") + f"checksum_sha256: {manifest['checksum_sha256']}\n",
            encoding="utf-8",
        )
    tar_path = tmp_path / f"{name}-{version}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(pkg_dir, arcname=".")
    return tar_path


def test_install_and_list(tmp_path):
    registry = CapabilityRegistry(tmp_path)
    tar_path = make_package(tmp_path, "cap-one", "1.0.0")
    pkg = registry.install(tar_path)

    assert pkg.name == "cap-one"
    assert registry.get("cap-one") is not None
    installed = registry.list()
    assert len(installed) == 1
    assert installed[0].checksum_sha256


def test_upgrade_overwrites(tmp_path):
    registry = CapabilityRegistry(tmp_path)
    v1 = make_package(tmp_path, "cap-two", "1.0.0")
    v2 = make_package(tmp_path, "cap-two", "1.1.0")
    registry.install(v1)
    registry.install(v2)

    installed = registry.get("cap-two")
    assert installed.version == "1.1.0"


def test_checksum_mismatch_raises(tmp_path):
    registry = CapabilityRegistry(tmp_path)
    tar_path = make_package(tmp_path, "cap-bad", "0.1.0", checksum=False)
    # Write a bogus checksum to manifest
    pkg_dir = tmp_path / "cap-bad-0.1.0"
    manifest = pkg_dir / "capability.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "checksum_sha256: deadbeef\n",
        encoding="utf-8",
    )
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(pkg_dir, arcname=".")

    try:
        registry.install(tar_path)
        assert False, "Expected checksum mismatch"
    except ValueError:
        assert True
