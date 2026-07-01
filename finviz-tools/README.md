# General ICM Workflow

A reusable, folder-based workflow for arbitrary agent tasks.

## How to use

1. Put the task in `00_input/request.md`
2. Read `01_intake/CONTEXT.md` and run the intake stage
3. Read `02_plan/CONTEXT.md` and produce a plan
4. Read `03_execute/CONTEXT.md` and produce the working output
5. Read `04_review/CONTEXT.md` and finalize the result

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
