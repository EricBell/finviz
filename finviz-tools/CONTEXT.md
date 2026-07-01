# Workspace Context

This workspace uses a general ICM-style workflow for arbitrary tasks.

## Routing

- `00_input/` contains the current task request
- `01_intake/` normalizes the request into structured criteria
- `02_plan/` creates an execution plan
- `03_execute/` performs the work
- `04_review/` checks the result and produces the final output

## Rules

- Load only the current stage plus any required shared files.
- Treat stage outputs as editable handoff artifacts.
- Prefer simple text files and JSON over opaque formats.
