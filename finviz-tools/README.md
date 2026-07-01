# General ICM Workflow

A reusable, folder-based workflow for arbitrary agent tasks.

## How to use

Run stages with `uv run`.

1. Put the task in `00_input/request.md`
2. Run `uv run run_stage.py 01_intake`
3. Run `uv run run_stage.py 02_plan`
4. Run `uv run run_stage.py 03_execute`
5. Run `uv run run_stage.py 04_review`

## Structure

- `00_input/` — user request
- `01_intake/` — normalize the request
- `02_plan/` — break the task into steps
- `03_execute/` — carry out the work
- `04_review/` — verify and finalize
- `shared/` — reusable conventions and templates

## Notes

- Keep each stage focused on one job.
- Use plain text and JSON for handoffs.
- Human edits are allowed between stages.
- Prefer `uv` for environment and script execution.
