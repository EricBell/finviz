#!/usr/bin/env -S uv run python
"""Review stage template.

Reads the draft and produces a final pass plus review notes.
"""

from __future__ import annotations

from pathlib import Path

STAGE_DIR = Path(__file__).resolve().parent
INTAKE_DIR = STAGE_DIR.parent / "01_intake" / "output"
PLAN_DIR = STAGE_DIR.parent / "02_plan" / "output"
EXEC_DIR = STAGE_DIR.parent / "03_execute" / "output"
OUTPUT_DIR = STAGE_DIR / "output"
FINAL_MD = OUTPUT_DIR / "final.md"
REVIEW_MD = OUTPUT_DIR / "review-notes.md"


def main() -> None:
    task_text = (INTAKE_DIR / "task.json").read_text(encoding="utf-8")
    plan_text = (PLAN_DIR / "plan.json").read_text(encoding="utf-8")
    draft_text = (EXEC_DIR / "draft.md").read_text(encoding="utf-8")

    review = [
        "# Review Notes",
        "",
        "- Draft received and reviewed.",
        "- Replace generic draft content with task-specific final output when ready.",
        "",
        "## Inputs Present",
        f"- task.json: yes ({len(task_text)} bytes)",
        f"- plan.json: yes ({len(plan_text)} bytes)",
        f"- draft.md: yes ({len(draft_text)} bytes)",
        "",
    ]

    final = [
        "# Final Output",
        "",
        draft_text.strip(),
        "",
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_MD.write_text("\n".join(final), encoding="utf-8")
    REVIEW_MD.write_text("\n".join(review), encoding="utf-8")

    print(f"Wrote {FINAL_MD}")
    print(f"Wrote {REVIEW_MD}")


if __name__ == "__main__":
    main()
