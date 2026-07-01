"""Helper to import a numbered stage's stage.py by path.

The stage folders (01_intake, 03_execute, ...) all contain a module named
`stage`, and their folder names aren't valid Python package identifiers, so
tests load each one explicitly by file path instead of via `import`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

TOOLS_ROOT = Path(__file__).resolve().parent.parent


def load_stage(folder_name: str) -> ModuleType:
    module_name = f"_stage_{folder_name}"
    if module_name in sys.modules:
        return sys.modules[module_name]

    stage_path = TOOLS_ROOT / folder_name / "stage.py"
    spec = importlib.util.spec_from_file_location(module_name, stage_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
