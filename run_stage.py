#!/usr/bin/env -S uv run python
"""Generic stage runner for the ICM-style workspace.

Usage:
  uv run run_stage.py 01_intake
  uv run run_stage.py 02_plan
  uv run run_stage.py 03_execute
  uv run run_stage.py 04_review

The runner simply executes <stage>/stage.py from within that stage directory.
Each stage is responsible for reading its declared inputs and writing outputs.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_stage(stage_name: str) -> int:
    stage_dir = ROOT / "finviz-tools" / stage_name
    stage_script = stage_dir / "stage.py"

    if not stage_script.exists():
        print(f"Missing stage script: {stage_script}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    pythonpath = [str(ROOT / "finviz-tools"), str(ROOT)]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)

    result = subprocess.run(
        [sys.executable, str(stage_script)],
        cwd=stage_dir,
        env=env,
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", help="Stage folder name, e.g. 01_intake")
    args = parser.parse_args()
    return run_stage(args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
