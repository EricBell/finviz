#!/usr/bin/env -S uv run python
"""Intake stage.

Reads the raw task request and emits a structured task.json plus notes.md.
For Finviz-like requests, this stage infers a workflow payload automatically.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

STAGE_DIR = Path(__file__).resolve().parent
INPUT_FILE = STAGE_DIR.parent / "00_input" / "request.md"
OUTPUT_DIR = STAGE_DIR / "output"
TASK_JSON = OUTPUT_DIR / "task.json"
NOTES_MD = OUTPUT_DIR / "notes.md"

FINVIZ_HINTS = (
    "finviz",
    "screener",
    "screen",
    "scanner",
    "scan",
    "stock",
    "stocks",
    "ticker",
    "tickers",
    "gap",
    "gapping",
    "market cap",
    "marketcap",
    "volume",
    "news",
    "insider",
    "analyst",
    "price target",
    "rating",
    "quote",
)

COMMON_TICKER_BLACKLIST = {
    "A",
    "AI",
    "AM",
    "AND",
    "API",
    "AS",
    "AT",
    "BE",
    "BY",
    "CEO",
    "ETF",
    "FOR",
    "GDP",
    "I",
    "IN",
    "IT",
    "LLC",
    "PM",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "SEC",
    "THE",
    "TO",
    "US",
}


def _clean_request_text(request_text: str) -> str:
    return "\n".join(line.rstrip() for line in request_text.strip().splitlines()).strip()


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _requested_limit(text: str) -> int | None:
    match = re.search(
        r"\b(?:top|first|return|show|give me|select)\s+(?:the\s+)?(\d{1,3})\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d{1,3})\s+(?:strongest|best|top|lowest|highest)\b", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_tickers(text: str) -> list[str]:
    tickers: list[str] = []
    for token in re.findall(r"\b[A-Z]{1,5}\b", text):
        if token in COMMON_TICKER_BLACKLIST:
            continue
        if token not in tickers:
            tickers.append(token)
    return tickers


def _infer_mode(text: str, tickers: list[str]) -> str:
    lowered = text.lower()

    if any(word in lowered for word in ("insider", "inside trading")):
        return "insider"
    if any(word in lowered for word in ("analyst", "price target", "rating", "target")):
        return "analyst"
    if "news" in lowered:
        return "news"
    if tickers and any(word in lowered for word in ("quote", "stock data", "fundamentals", "profile")):
        return "stock"
    return "screen"


def _small_cap_filter(text: str) -> tuple[list[str], list[str]]:
    lowered = text.lower()
    filters: list[str] = []
    assumptions: list[str] = []

    if "micro cap" in lowered:
        filters.append("cap_micro")
        assumptions.append("Interpreted 'micro cap' as Finviz cap_micro.")
    elif "small cap" in lowered:
        filters.append("cap_small")
        assumptions.append("Interpreted 'small cap' as Finviz cap_small.")
    elif "mid cap" in lowered:
        filters.append("cap_mid")
        assumptions.append("Interpreted 'mid cap' as Finviz cap_mid.")
    elif "large cap" in lowered:
        filters.append("cap_large")
        assumptions.append("Interpreted 'large cap' as Finviz cap_large.")

    return filters, assumptions


def _gap_filter(text: str) -> tuple[list[str], list[str]]:
    lowered = text.lower()
    filters: list[str] = []
    assumptions: list[str] = []

    if "gap" not in lowered:
        return filters, assumptions

    match = re.search(r"gap(?:ping)?\s+up\s*(?:by|at|of)?\s*(\d{1,2})\s*%", lowered)
    if not match:
        match = re.search(r"\b(\d{1,2})\s*%\s*gap", lowered)

    if match:
        gap_pct = max(0, min(20, int(match.group(1))))
    else:
        gap_pct = 3
        assumptions.append("Interpreted 'gapping up' as a 3%+ gap filter.")

    filters.append(f"ta_gap_u{gap_pct}")
    if not assumptions:
        assumptions.append(f"Interpreted gap up as Finviz ta_gap_u{gap_pct}.")

    return filters, assumptions


def _screen_criteria(text: str) -> tuple[dict[str, Any], list[str], list[str]]:
    criteria: dict[str, Any] = {}
    assumptions: list[str] = []
    open_questions: list[str] = []

    filters: list[str] = []
    cap_filters, cap_assumptions = _small_cap_filter(text)
    gap_filters, gap_assumptions = _gap_filter(text)
    filters.extend(cap_filters)
    filters.extend(gap_filters)
    assumptions.extend(cap_assumptions)
    assumptions.extend(gap_assumptions)

    lowered = text.lower()
    order = ""
    if any(word in lowered for word in ("strongest", "best", "most bullish", "highest momentum")):
        order = "-change"
        assumptions.append("Used price change as a proxy for 'strongest'.")
    elif "volume" in lowered or "liquidity" in lowered:
        order = "-volume"
        assumptions.append("Used volume as a proxy for strength.")

    requested_limit = _requested_limit(text)
    if requested_limit is not None:
        limit = requested_limit
    elif any(word in lowered for word in ("strongest", "top", "best")):
        limit = 5
    else:
        limit = 10

    criteria["filters"] = filters
    criteria["rows"] = limit
    if order:
        criteria["order"] = order
    criteria["table"] = "Overview"
    criteria["request_method"] = "sequential"
    criteria["sort_hint"] = ["gap", "volume", "liquidity"]

    if not filters:
        open_questions.append("No explicit screener filters were inferred; review the request before execution.")

    return criteria, assumptions, open_questions


def _build_finviz_workflow(request_text: str) -> tuple[dict[str, Any], list[str], list[str]]:
    tickers = _extract_tickers(request_text)
    mode = _infer_mode(request_text, tickers)
    workflow: dict[str, Any] = {"domain": "finviz", "mode": mode}
    assumptions: list[str] = []
    open_questions: list[str] = []

    if mode == "screen":
        criteria, screen_assumptions, screen_questions = _screen_criteria(request_text)
        workflow["criteria"] = criteria
        assumptions.extend(screen_assumptions)
        open_questions.extend(screen_questions)
        if tickers:
            workflow["criteria"]["tickers"] = tickers
    elif mode == "stock":
        workflow["criteria"] = {"tickers": tickers[:1] if tickers else []}
    elif mode in {"news", "insider", "analyst"}:
        workflow["criteria"] = {"ticker": tickers[:1] if tickers else None}
        if not tickers:
            open_questions.append("No ticker symbol detected for the requested Finviz lookup.")
    else:
        workflow["criteria"] = {}

    return workflow, assumptions, open_questions


def normalize_request(request_text: str) -> dict:
    request_text = _clean_request_text(request_text)
    lowered = request_text.lower()
    objective = request_text.splitlines()[0] if request_text else None

    task: dict[str, Any] = {
        "request": request_text,
        "objective": objective,
        "constraints": [],
        "expected_output": None,
        "assumptions": [],
        "open_questions": [],
    }

    if _contains_any(lowered, FINVIZ_HINTS):
        workflow, assumptions, open_questions = _build_finviz_workflow(request_text)
        task["workflow"] = workflow
        task["expected_output"] = "A Finviz result set or lookup based on the inferred mode."
        task["assumptions"].extend(assumptions)
        task["open_questions"].extend(open_questions)
        task["objective"] = f"Finviz {workflow.get('mode', 'screen')} request"
        if workflow.get("mode") == "screen":
            task["constraints"].append("Use Finviz filters and return a concise result set.")
        else:
            task["constraints"].append("Use the inferred Finviz lookup mode.")
    else:
        task["objective"] = objective
        task["expected_output"] = "A structured response matching the request."

    return task


def render_notes(task: dict) -> str:
    workflow = task.get("workflow") or {}
    lines = [
        "# Intake Notes",
        "",
        "## Request",
        task["request"],
        "",
        "## Objective",
        str(task.get("objective")),
        "",
        "## Workflow",
        "```json",
        json.dumps(workflow, indent=2, ensure_ascii=False),
        "```",
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

    lines.extend(["", "## Open Questions"])
    open_questions = task.get("open_questions") or []
    if open_questions:
        lines.extend(f"- {item}" for item in open_questions)
    else:
        lines.append("- none recorded")

    lines.extend(["", "## Expected Output", str(task.get("expected_output")), ""])
    return "\n".join(lines)


def main() -> None:
    request_text = INPUT_FILE.read_text(encoding="utf-8")
    task = normalize_request(request_text)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TASK_JSON.write_text(json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    NOTES_MD.write_text(render_notes(task), encoding="utf-8")

    print(f"Wrote {TASK_JSON}")
    print(f"Wrote {NOTES_MD}")


if __name__ == "__main__":
    main()
