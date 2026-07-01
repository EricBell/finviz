#!/bin/bash
uv run run_stage.py 01_intake
uv run run_stage.py 02_plan
uv run run_stage.py 03_execute
uv run run_stage.py 04_review
