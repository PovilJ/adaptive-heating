"""Offline release validation and recoverable installation, independently tested."""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

from .const import DOMAIN, REPOSITORY

MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_EXPANDED_BYTES = 30 * 1024 * 1024


def version_tuple(version: str) -> tuple[int, int, int]:
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("A stable three-part version is required")
    return tuple(int(part) for part in version.split("."))


def release_info(response: dict) -> dict:
    if response.get("draft") or response.get("prerelease"):
        raise ValueError("Only stable published releases are supported")
    tag = response.get("tag_name", "")
    version = tag.removeprefix("v")
    version_tuple(version)
    name = f"{DOMAIN}-{version}.zip"
    assets = {item.get("name"): item.get("browser_download_url") for item in response.get("assets", [])}
    base = f"https://github.com/{REPOSITORY}/releases/download/{tag}/"
    for asset in (name, name + ".sha256"):
        if assets.get(asset) != base + asset:
            raise ValueError("Expected release archive and checksum assets are missing")
    return {"version": version, "url": assets[name], "checksum_url": assets[name + ".sha256"],
            "notes": str(response.get("body") or "")[:20000],
            "release_url": f"https://github.com/{REPOSITORY}/releases/tag/{tag}"}


def validate_archive(blob: bytes, checksum: str, expected_version: str, ha_version: str) -> dict[str, bytes]:
    if len(blob) > MAX_ARCHIVE_BYTES:
        raise ValueError("Release archive is too large")
    digest = checksum.strip().split()[0] if checksum.strip() else ""
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or hashlib.sha256(blob).hexdigest() != digest:
        raise ValueError("Release checksum does not match")
    files = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        if len(archive.infolist()) > 300:
            raise ValueError("Too many archive entries")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename or not path.parts or path.parts[0] != DOMAIN:
                raise ValueError("Unsafe archive path")
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Archive symlinks are not allowed")
            if item.is_dir():
                continue
            relative = path.relative_to(DOMAIN)
            if not relative.parts or relative.suffix not in (".py", ".json", ".md"):
                raise ValueError("Unexpected file type")
            name = str(relative)
            if name in files:
                raise ValueError("Duplicate archive member")
            total += item.file_size
            if total > MAX_EXPANDED_BYTES:
                raise ValueError("Expanded archive is too large")
            contents = archive.read(item)
            if relative.suffix == ".json":
                json.loads(contents)
            elif relative.suffix == ".py":
                ast.parse(contents, filename=name)
            files[name] = contents
    for required in ("manifest.json", "release.json", "__init__.py", "config_flow.py", "const.py", "engine.py", "updater.py",
                     "coordinator.py", "entity.py", "sensor.py", "number.py", "select.py", "button.py", "update.py",
                     "release.py", "strings.json", "translations/en.json"):
        if required not in files:
            raise ValueError(f"Release missing {required}")
    manifest = json.loads(files["manifest.json"])
    metadata = json.loads(files["release.json"])
    if manifest.get("domain") != DOMAIN or manifest.get("version") != expected_version:
        raise ValueError("Manifest does not match the selected release")
    if metadata.get("version") != expected_version or metadata.get("repository") != REPOSITORY:
        raise ValueError("Release metadata mismatch")
    if version_tuple(ha_version) < version_tuple(metadata.get("minimum_home_assistant", "")):
        raise ValueError("This release requires a newer Home Assistant version")
    constants = ast.parse(files["const.py"])
    versions = [n.value.value for n in constants.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in n.targets)
                and isinstance(n.value, ast.Constant)]
    if versions != [expected_version]:
        raise ValueError("Runtime version does not match manifest")
    return files


def install_files(files: dict[str, bytes], destination: Path, backup_parent: Path) -> str:
    """Stage in the same filesystem; restore old directory if activation fails.

    This function never touches HA configuration entries or learned-state files.
    Keep the previous code in a named backup, outside custom_components.
    """
    destination = Path(destination)
    if destination.name != DOMAIN or destination.is_symlink() or not destination.is_dir():
        raise ValueError("Unexpected installation directory")
    backup_parent.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="previous-", dir=backup_parent)) / DOMAIN
    with tempfile.TemporaryDirectory(prefix=".adaptive-heating-stage-", dir=destination.parent) as temp:
        stage = Path(temp) / DOMAIN
        stage.mkdir()
        for name, contents in files.items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError("Unsafe staged path")
            target = stage.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
        os.replace(destination, backup)
        try:
            os.replace(stage, destination)
        except BaseException:
            os.replace(backup, destination)
            raise
    return str(backup)
