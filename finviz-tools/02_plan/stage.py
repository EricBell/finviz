#!/usr/bin/env -S uv run python
"""Plan stage template.

Reads the normalized task from intake and emits a simple execution plan.
This is a generic skeleton; replace the planning heuristics with an LLM call
or domain-specific planner when ready.
"""

from __future__ import annotations

import json
from pathlib import Path

STAGE_DIR = Path(__file__).resolve().parent
INPUT_DIR = STAGE_DIR.parent / "01_intake" / "output"
TASK_JSON = INPUT_DIR / "task.json"
NOTES_MD = INPUT_DIR / "notes.md"
OUTPUT_DIR = STAGE_DIR / "output"
PLAN_JSON = OUTPUT_DIR / "plan.json"
PLAN_MD = OUTPUT_DIR / "plan.md"


def make_plan(task: dict) -> dict:
    return {
        "objective": task.get("objective"),
        "steps": [
            {
                "name": "execute",
                "description": "Perform the requested work using the structured task and any shared helpers.",
            },
            {
                "name": "review",
                "description": "Validate the output against the task and summarize any issues.",
            },
        ],
        "dependencies": ["01_intake/output/task.json", "01_intake/output/notes.md"],
        "risks": ["Task may be underspecified and require assumptions."],
    }


def render_plan(plan: dict) -> str:
    lines = [
        "# Execution Plan",
        "",
        f"## Objective",
        str(plan.get("objective")),
        "",
        "## Steps",
    ]
    for step in plan.get("steps", []):
        lines.append(f"- {step['name']}: {step['description']}")
    lines.extend([
        "",
        "## Dependencies",
    ])
    for dep in plan.get("dependencies", []):
        lines.append(f"- {dep}")
    lines.extend([
        "",
        "## Risks",
    ])
    for risk in plan.get("risks", []):
        lines.append(f"- {risk}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    task = json.loads(TASK_JSON.read_text(encoding="utf-8"))
    _notes = NOTES_MD.read_text(encoding="utf-8")

    plan = make_plan(task)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_JSON.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    PLAN_MD.write_text(render_plan(plan), encoding="utf-8")

    print(f"Wrote {PLAN_JSON}")
    print(f"Wrote {PLAN_MD}")


if __name__ == "__main__":
    main()
