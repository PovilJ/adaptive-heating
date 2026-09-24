#!/usr/bin/env python3
"""Build reproducible, integration-only release assets. Never packages /config."""

from pathlib import Path
import ast
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "custom_components" / "adaptive_heating"


def build():
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    release = json.loads((SOURCE / "release.json").read_text())
    version = manifest["version"]
    if release["version"] != version:
        raise ValueError("Release and manifest versions differ")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    archive = output / f"adaptive_heating-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for file in sorted(SOURCE.rglob("*")):
            if not file.is_file() or file.suffix not in (".py", ".json", ".md"):
                continue
            if file.is_symlink() or any(part.startswith(".") for part in file.relative_to(SOURCE).parts):
                raise ValueError("Unexpected hidden file or symlink")
            data = file.read_bytes()
            if file.suffix == ".json":
                json.loads(data)
            elif file.suffix == ".py":
                ast.parse(data, filename=str(file))
            info = zipfile.ZipInfo("adaptive_heating/" + file.relative_to(SOURCE).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n")
    print(archive)
    return archive


if __name__ == "__main__":
    build()
