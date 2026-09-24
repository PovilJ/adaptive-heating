#!/usr/bin/env python3
"""Install a verified local release archive. Does not restart or enable control."""

import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--config", type=Path, default=Path("/config"))
    parser.add_argument("--ha-version", help="Required if the target has no .HA_VERSION file")
    parser.add_argument("--check", action="store_true", help="Validate only; do not install")
    parser.add_argument("--update", action="store_true", help="Replace an existing installation, preserving a code backup")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    package = types.ModuleType("adaptive_heating_release_tools")
    package.__path__ = [str(root / "custom_components" / "adaptive_heating")]
    sys.modules[package.__name__] = package
    release = importlib.import_module(package.__name__ + ".release")
    version_file = args.config / ".HA_VERSION"
    ha_version = args.ha_version or (version_file.read_text().strip() if version_file.is_file() else "")
    expected = json.loads((root / "custom_components/adaptive_heating/manifest.json").read_text())["version"]
    files = release.validate_archive(args.archive.read_bytes(),
        args.archive.with_suffix(args.archive.suffix + ".sha256").read_text(), expected, ha_version)
    destination = args.config / "custom_components" / "adaptive_heating"
    if args.check:
        print(f"Validated {len(files)} integration files for {expected}; no files installed.")
        return
    if destination.exists():
        if not args.update:
            parser.error("Already installed; use the HA update entity or pass --update explicitly")
        backup = release.install_files(files, destination, args.config / ".adaptive_heating_backups")
        print(f"Previous code backed up to {backup}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".adaptive-heating-install-", dir=destination.parent) as temp:
            stage = Path(temp) / "adaptive_heating"
            stage.mkdir()
            for name, contents in files.items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(contents)
            os.replace(stage, destination)
    print("Installed. Restart Home Assistant manually, then add Adaptive Heating. Initial mode: Observe.")


if __name__ == "__main__":
    main()
