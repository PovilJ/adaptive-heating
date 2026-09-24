"""Exercise release rejection, installation, and recovery in temporary folders."""

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from common import SOURCE, module

release = module("release")
VERSION = module("const").VERSION


def files():
    return {p.relative_to(SOURCE).as_posix(): p.read_bytes() for p in SOURCE.rglob("*")
            if p.is_file() and p.suffix in (".py", ".json")}


def archive(overrides=None):
    contents = files() | (overrides or {})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as bundle:
        for name, data in contents.items():
            bundle.writestr("adaptive_heating/" + name, data)
    blob = stream.getvalue()
    return blob, hashlib.sha256(blob).hexdigest()


class ArchiveValidation(unittest.TestCase):
    def test_real_component_package_validates(self):
        blob, digest = archive()
        checked = release.validate_archive(blob, digest, VERSION, "2026.7.4")
        self.assertIn("coordinator.py", checked)
        self.assertNotIn("tests/test_engine.py", checked)

    def test_corruption_rejected_before_installation(self):
        blob, digest = archive()
        with self.assertRaisesRegex(ValueError, "checksum"):
            release.validate_archive(blob + b"corrupt", digest, VERSION, "2026.7.4")

    def test_traversal_cannot_overwrite_ha_configuration(self):
        blob, digest = archive({"../../configuration.yaml": b"bad"})
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            release.validate_archive(blob, digest, VERSION, "2026.7.4")

    def test_incompatible_home_assistant_rejected(self):
        blob, digest = archive()
        with self.assertRaisesRegex(ValueError, "newer Home Assistant"):
            release.validate_archive(blob, digest, VERSION, "2025.12.0")

    def test_version_must_match_selected_release(self):
        blob, digest = archive()
        with self.assertRaisesRegex(ValueError, "Manifest"):
            release.validate_archive(blob, digest, "99.0.0", "2026.7.4")

    def test_invalid_python_rejected(self):
        blob, digest = archive({"engine.py": b"def bad(:"})
        with self.assertRaises(SyntaxError):
            release.validate_archive(blob, digest, VERSION, "2026.7.4")

    def test_runtime_and_manifest_versions_must_match(self):
        content = (SOURCE / "const.py").read_bytes().replace(f'VERSION = "{VERSION}"'.encode(), b'VERSION = "99.0.0"')
        blob, digest = archive({"const.py": content})
        with self.assertRaisesRegex(ValueError, "Runtime"):
            release.validate_archive(blob, digest, VERSION, "2026.7.4")

    def test_stable_versions_are_compared_numerically(self):
        self.assertGreater(release.version_tuple("0.10.0"), release.version_tuple("0.9.0"))
        for value in ("main", "v0.1.0", "0.1.0-beta", "0.1"):
            with self.assertRaises(ValueError):
                release.version_tuple(value)


class ReleaseDiscovery(unittest.TestCase):
    def response(self):
        base = "https://github.com/PovilJ/adaptive-heating/releases/download/v0.1.0/"
        names = ("adaptive_heating-0.1.0.zip", "adaptive_heating-0.1.0.zip.sha256")
        return {"tag_name": "v0.1.0", "prerelease": False, "draft": False,
                "assets": [{"name": n, "browser_download_url": base + n} for n in names], "body": "Release notes"}

    def test_stable_release_is_recognized(self):
        self.assertEqual(release.release_info(self.response())["version"], "0.1.0")

    def test_draft_and_prerelease_are_not_offered(self):
        for flag in ("draft", "prerelease"):
            with self.assertRaises(ValueError):
                release.release_info(self.response() | {flag: True})

    def test_download_from_another_repository_is_rejected(self):
        data = self.response()
        data["assets"][0]["browser_download_url"] = "https://example.com/archive.zip"
        with self.assertRaises(ValueError):
            release.release_info(data)

    def test_source_code_archive_is_not_an_installable_release(self):
        with self.assertRaises(ValueError):
            release.release_info(self.response() | {"assets": []})


class RecoverableInstallation(unittest.TestCase):
    def test_settings_are_preserved_and_old_code_is_backed_up(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "custom_components/adaptive_heating"
            destination.mkdir(parents=True)
            (destination / "old.py").write_text("old code")
            storage = root / ".storage"
            storage.mkdir()
            saved = storage / "adaptive_heating.example"
            saved.write_text('{"target": 23}')
            backup = Path(release.install_files({"__init__.py": b"# new"}, destination, root / "backups"))
            self.assertEqual((backup / "old.py").read_text(), "old code")
            self.assertEqual(saved.read_text(), '{"target": 23}')
            self.assertEqual((destination / "__init__.py").read_text(), "# new")
            self.assertFalse((destination / "old.py").exists())

    def test_failed_activation_restores_old_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "custom_components/adaptive_heating"
            destination.mkdir(parents=True)
            (destination / "old.py").write_text("old code")
            original_replace = release.os.replace
            calls = 0
            def fail_second(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("Simulated disk failure")
                return original_replace(source, target)
            with patch.object(release.os, "replace", side_effect=fail_second):
                with self.assertRaises(OSError):
                    release.install_files({"__init__.py": b"# new"}, destination, root / "backups")
            self.assertEqual((destination / "old.py").read_text(), "old code")


if __name__ == "__main__":
    unittest.main()
