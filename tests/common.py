"""Import the pure modules without installing or starting Home Assistant."""

import importlib
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "custom_components" / "adaptive_heating"
PACKAGE = "adaptive_heating_test_package"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(SOURCE)]
    sys.modules[PACKAGE] = package


def module(name):
    return importlib.import_module(PACKAGE + "." + name)
