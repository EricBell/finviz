#!/usr/bin/env -S uv run python
"""Execute stage template.

Reads the plan and produces a draft result. In a real workspace, this stage can
call shared helpers, scrape data, or generate artifacts specific to the task.
"""

from __future__ import annotations

import json
from pathlib import Path

STAGE_DIR = Path(__file__).resolve().parent
INTAKE_DIR = STAGE_DIR.parent / "01_intake" / "output"
PLAN_DIR = STAGE_DIR.parent / "02_plan" / "output"
OUTPUT_DIR = STAGE_DIR / "output"
ARTIFACTS_DIR = OUTPUT_DIR / "artifacts"
DRAFT_MD = OUTPUT_DIR / "draft.md"


def build_draft(task: dict, plan: dict) -> str:
    lines = [
        "# Draft Output",
        "",
        "## Objective",
        str(task.get("objective")),
        "",
        "## Constraints",
    ]
    constraints = task.get("constraints") or []
    if constraints:
        lines.extend(f"- {item}" for item in constraints)
    else:
        lines.append("- none recorded")

    lines.extend([
        "",
        "## Assumptions",
    ])
    assumptions = task.get("assumptions") or []
    if assumptions:
        lines.extend(f"- {item}" for item in assumptions)
    else:
        lines.append("- none recorded")

    lines.extend([
        "",
        "## Plan Summary",
    ])
    for step in plan.get("steps", []):
        lines.append(f"- {step['name']}: {step['description']}")

    lines.extend([
        "",
        "## Result",
        "Replace this section with the task-specific output.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    task = json.loads((INTAKE_DIR / "task.json").read_text(encoding="utf-8"))
    plan = json.loads((PLAN_DIR / "plan.json").read_text(encoding="utf-8"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    DRAFT_MD.write_text(build_draft(task, plan), encoding="utf-8")

    print(f"Wrote {DRAFT_MD}")


if __name__ == "__main__":
    main()
