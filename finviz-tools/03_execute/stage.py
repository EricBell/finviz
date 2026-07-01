#!/usr/bin/env -S uv run python
"""Execute stage.

Reads the plan and produces a draft result. If the task contains Finviz-specific
criteria, this stage routes to the reusable shared.finviz helpers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STAGE_DIR = Path(__file__).resolve().parent
INTAKE_DIR = STAGE_DIR.parent / "01_intake" / "output"
PLAN_DIR = STAGE_DIR.parent / "02_plan" / "output"
OUTPUT_DIR = STAGE_DIR / "output"
ARTIFACTS_DIR = OUTPUT_DIR / "artifacts"
DRAFT_MD = OUTPUT_DIR / "draft.md"

PRIORITY_COLUMNS = [
    "Ticker",
    "Company",
    "Price",
    "Change",
    "Gap",
    "Gap %",
    "Relative Volume",
    "Volume",
    "Market Cap",
    "Sector",
    "Industry",
    "Country",
]


def _get_task_text(task: dict) -> str:
    return str(task.get("request") or "").strip()


def _find_finviz_payload(task: dict) -> dict[str, Any] | None:
    if isinstance(task.get("finviz"), dict):
        return dict(task["finviz"])
    if isinstance(task.get("criteria"), dict):
        return {"criteria": dict(task["criteria"])}

    workflow = task.get("workflow")
    if isinstance(workflow, dict):
        if isinstance(workflow.get("finviz"), dict):
            return dict(workflow["finviz"])
        if workflow.get("domain") == "finviz":
            return dict(workflow)

    return None


def _extract_finviz_criteria(task: dict) -> tuple[dict[str, Any], str, str]:
    payload = _find_finviz_payload(task) or {}
    criteria = payload.get("criteria") if isinstance(payload.get("criteria"), dict) else {}

    if not criteria:
        criteria = {
            key: value
            for key, value in payload.items()
            if key not in {"mode", "operation", "action", "criteria", "tool"}
        }

    tool = str(payload.get("tool") or payload.get("mode") or payload.get("operation") or payload.get("action") or criteria.get("tool") or "finviz.screen").strip().lower()
    mode = tool.split(".")[-1]
    return criteria, mode, tool


def _should_use_finviz(task: dict) -> bool:
    return _find_finviz_payload(task) is not None


def _escape_md(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _select_columns(rows: list[dict]) -> list[str]:
    if not rows:
        return []
    columns = [col for col in PRIORITY_COLUMNS if any(col in row for row in rows)]
    if columns:
        return columns
    first = rows[0]
    return list(first.keys())[:8]


def _rank_rows(rows: list[dict], ranking: dict) -> list[dict]:
    primary = str(ranking.get("primary") or ranking.get("sort_by") or "").lower()
    direction = str(ranking.get("direction") or "desc").lower()

    def _num(value: Any) -> float:
        if value is None:
            return float("-inf")
        s = str(value).replace(",", "").replace("%", "").strip()
        try:
            return float(s)
        except ValueError:
            return float("-inf")

    def _key(row: dict) -> float:
        if primary in {"change", "price change", "change_from_open", "change from open"}:
            return _num(row.get("Change"))
        if primary in {"volume", "vol"}:
            return _num(row.get("Volume"))
        if primary in {"market_cap", "market cap", "cap"}:
            return _num(str(row.get("Market Cap", "")).replace("B", "000").replace("M", ""))
        if primary in {"relative_volume", "rvol", "relative volume"}:
            return _num(row.get("Relative Volume") or row.get("Rel Volume"))
        return _num(row.get("Change"))

    return sorted(rows, key=_key, reverse=direction != "asc")


def _render_markdown_table(rows: list[dict], limit: int = 10) -> str:
    if not rows:
        return "No results."

    columns = _select_columns(rows)
    if not columns:
        return "No tabular fields returned."

    visible = rows[:limit]
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in visible:
        body.append("| " + " | ".join(_escape_md(row.get(col, "")) for col in columns) + " |")
    return "\n".join([header, divider, *body])


def _render_generic_draft(task: dict, plan: dict) -> str:
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

    lines.extend(["", "## Assumptions"])
    assumptions = task.get("assumptions") or []
    if assumptions:
        lines.extend(f"- {item}" for item in assumptions)
    else:
        lines.append("- none recorded")

    lines.extend(["", "## Plan Summary"])
    for step in plan.get("steps", []):
        lines.append(f"- {step['name']}: {step['description']}")

    lines.extend([
        "",
        "## Result",
        "Replace this section with the task-specific output.",
        "",
    ])
    return "\n".join(lines)


def _run_finviz(task: dict, plan: dict) -> str:
    from shared.finviz import (
        compile_semantic_filters,
        get_all_news,
        get_analyst_targets,
        get_insider,
        get_news,
        get_stock,
        screen,
    )

    criteria, mode, tool = _extract_finviz_criteria(task)
    limit = int(criteria.get("limit") or criteria.get("rows") or 10)
    ranking = criteria.get("ranking") or {}

    result: dict[str, Any]
    artifact_path: Path

    if mode in {"stock", "quote", "quotes"}:
        tickers = criteria.get("tickers") or criteria.get("ticker") or []
        if isinstance(tickers, str):
            tickers = [tickers]
        result = {ticker: get_stock(ticker) for ticker in tickers}
        artifact_path = ARTIFACTS_DIR / "stock.json"
    elif mode in {"news"}:
        ticker = criteria.get("ticker") or criteria.get("tickers") or ""
        if isinstance(ticker, list):
            ticker = ticker[0] if ticker else ""
        result = {"ticker": ticker, "news": get_news(ticker) if ticker else get_all_news()}
        artifact_path = ARTIFACTS_DIR / "news.json"
    elif mode in {"insider"}:
        ticker = criteria.get("ticker") or criteria.get("tickers") or ""
        if isinstance(ticker, list):
            ticker = ticker[0] if ticker else ""
        result = {"ticker": ticker, "insider": get_insider(ticker) if ticker else []}
        artifact_path = ARTIFACTS_DIR / "insider.json"
    elif mode in {"analyst", "targets", "rating"}:
        ticker = criteria.get("ticker") or criteria.get("tickers") or ""
        if isinstance(ticker, list):
            ticker = ticker[0] if ticker else ""
        result = {
            "ticker": ticker,
            "analyst_targets": get_analyst_targets(ticker) if ticker else [],
        }
        artifact_path = ARTIFACTS_DIR / "analyst-targets.json"
    else:
        rows = screen(criteria)
        result = {"rows": rows, "count": len(rows), "criteria": criteria}
        artifact_path = ARTIFACTS_DIR / "screen.json"

        if ranking:
            rows = _rank_rows(rows, ranking)
            result["rows"] = rows

    artifact_path.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    lines = [
        "# Draft Output",
        "",
        "## Objective",
        str(task.get("objective") or task.get("request") or "Finviz task"),
        "",
        "## Finviz Mode",
        mode,
        "",
        "## Criteria",
        "```json",
        json.dumps(criteria, indent=2, default=str),
        "```",
        "",
    ]

    if "rows" in result:
        rows = result["rows"]
        lines.extend([
            "## Result",
            f"Rows: {result['count']}",
            "",
            _render_markdown_table(rows, limit=limit),
            "",
            f"Raw artifact: `{artifact_path.name}`",
            "",
        ])
    else:
        lines.extend([
            "## Result",
            "```json",
            json.dumps(result, indent=2, default=str),
            "```",
            "",
            f"Raw artifact: `{artifact_path.name}`",
            "",
        ])

    return "\n".join(lines)


def main() -> None:
    task = json.loads((INTAKE_DIR / "task.json").read_text(encoding="utf-8"))
    plan = json.loads((PLAN_DIR / "plan.json").read_text(encoding="utf-8"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    if _should_use_finviz(task):
        draft = _run_finviz(task, plan)
    else:
        draft = _render_generic_draft(task, plan)

    DRAFT_MD.write_text(draft, encoding="utf-8")

    print(f"Wrote {DRAFT_MD}")


if __name__ == "__main__":
    main()
