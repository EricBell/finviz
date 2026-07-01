#!/usr/bin/env -S uv run python
"""Intake stage template.

Reads the raw task request and emits a structured task.json plus notes.md.
This is a generic skeleton; replace the normalization heuristics with an LLM
call or domain-specific parser when you are ready.
"""

from __future__ import annotations

import json
from pathlib import Path

STAGE_DIR = Path(__file__).resolve().parent
INPUT_FILE = STAGE_DIR.parent / "00_input" / "request.md"
OUTPUT_DIR = STAGE_DIR / "output"
TASK_JSON = OUTPUT_DIR / "task.json"
NOTES_MD = OUTPUT_DIR / "notes.md"


def normalize_request(request_text: str) -> dict:
    """Return a minimal structured representation of the request."""
    return {
        "request": request_text.strip(),
        "objective": None,
        "constraints": [],
        "expected_output": None,
        "assumptions": [],
        "open_questions": [],
    }


def render_notes(task: dict) -> str:
    lines = [
        "# Intake Notes",
        "",
        "## Request",
        task["request"],
        "",
        "## Objective",
        str(task["objective"]),
        "",
        "## Constraints",
        "- none recorded",
        "",
        "## Assumptions",
        "- none recorded",
        "",
        "## Open Questions",
        "- none recorded",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    request_text = INPUT_FILE.read_text(encoding="utf-8")
    task = normalize_request(request_text)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TASK_JSON.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    NOTES_MD.write_text(render_notes(task), encoding="utf-8")

    print(f"Wrote {TASK_JSON}")
    print(f"Wrote {NOTES_MD}")


if __name__ == "__main__":
    main()
