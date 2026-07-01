#!/usr/bin/env -S uv run python
"""Intake stage.

Primary path: use an LLM to interpret the request and choose the tool +
parameters.
Fallback path: a small deterministic parser for when no LLM endpoint is
configured.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from shared.llm import LLMError, chat_json

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

SYSTEM_PROMPT = """You convert a user's request into a structured execution spec for an agent.
Return JSON only, no markdown.

Schema:
{
  "objective": string,
  "expected_output": string,
  "constraints": [string],
  "assumptions": [string],
  "open_questions": [string],
  "workflow": {
    "domain": "finviz" | "generic",
    "tool": "finviz.screen" | "finviz.stock" | "finviz.news" | "finviz.insider" | "finviz.analyst" | null,
    "mode": "screen" | "stock" | "news" | "insider" | "analyst" | null,
    "criteria": object
  }
}

Rules:
- Choose the single best tool.
- For Finviz screen requests, use semantic criteria, not raw Finviz tags.
- Preferred semantic fields:
  - sector, industry, exchange, index
  - market_cap: {"class": "large|mid|small|micro|nano"}
  - price: {"relation": "over|under", "value": number} or {"min": number, "max": number}
  - performance: {"change_from_open_gte": number, "gap_up_gte": number, "change_gte": number}
  - liquidity: {"relative_volume_gte": number, "average_volume_gte": number}
  - technical: {"sma": {"period": 20|50|200, "relation": "above|below|crossabove|crossbelow"}}
  - ticker or tickers if explicitly requested
  - limit and ranking
- Examples:
  - "top 5 large cap energy stocks up at least 3% since the open" ->
    domain finviz, tool finviz.screen, criteria {"sector":"Energy","market_cap":{"class":"large"},"performance":{"change_from_open_gte":3},"limit":5}
  - "low priced breakout stocks with relative volume above 2 and price above the 50 day moving average" ->
    criteria {"price":{"relation":"under","value":10},"liquidity":{"relative_volume_gte":2},"technical":{"sma":{"period":50,"relation":"above"}},"limit":7}
  - "price <$10 and >$2" ->
    criteria {"price":{"min":2,"max":10}}
- If the request is ambiguous, add assumptions and open questions.
"""


def _clean_request_text(request_text: str) -> str:
    return "\n".join(line.rstrip() for line in request_text.strip().splitlines()).strip()


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _requested_limit(text: str) -> int | None:
    match = re.search(r"\b(?:top|first|return|show|give me|select)\s+(?:the\s+)?(\d{1,3})\b", text, flags=re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d{1,3})\s+(?:strongest|best|top|lowest|highest)\b", text, flags=re.I)
    if match:
        return int(match.group(1))
    return None


def _semantic_fallback(request_text: str) -> dict[str, Any]:
    text = request_text.lower()
    task: dict[str, Any] = {
        "request": request_text,
        "objective": request_text.splitlines()[0] if request_text else None,
        "constraints": [],
        "expected_output": "A structured response matching the request.",
        "assumptions": [],
        "open_questions": [],
    }

    # Default to Finviz screen when the request looks market-related.
    workflow: dict[str, Any] = {"domain": "generic", "tool": None, "mode": None, "criteria": {}}
    if _contains_any(text, FINVIZ_HINTS):
        workflow.update({"domain": "finviz", "tool": "finviz.screen", "mode": "screen"})
        criteria: dict[str, Any] = {}

        if "energy" in text:
            criteria["sector"] = "Energy"
        if "large cap" in text:
            criteria["market_cap"] = {"class": "large"}
            task["assumptions"].append("Interpreted 'large cap' as a large-cap Finviz screen.")
        if "small cap" in text:
            criteria["market_cap"] = {"class": "small"}
        if "mid cap" in text:
            criteria["market_cap"] = {"class": "mid"}
        if "micro cap" in text:
            criteria["market_cap"] = {"class": "micro"}
        if "nano cap" in text:
            criteria["market_cap"] = {"class": "nano"}

        if "since the open" in text or "from the open" in text:
            match = re.search(r"(\d{1,2})\s*%.*?(?:since the open|from the open)", text)
            if not match:
                match = re.search(r"(?:since the open|from the open).*?(\d{1,2})\s*%", text)
            criteria.setdefault("performance", {})["change_from_open_gte"] = int(match.group(1)) if match else 3
        if "gap" in text:
            match = re.search(r"gap(?:ping)?\s+up\s*(?:by|at|of)?\s*(\d{1,2})\s*%", text)
            if not match:
                match = re.search(r"\b(\d{1,2})\s*%\s*gap", text)
            criteria.setdefault("performance", {})["gap_up_gte"] = int(match.group(1)) if match else 3
            if not match:
                task["assumptions"].append("Interpreted 'gapping up' as 3%+.")

        if any(phrase in text for phrase in ("relative volume", "rvol", "rel vol")):
            match = re.search(r"(?:relative volume|rvol|rel vol)\s*(?:above|over|>|>=)?\s*([\d.]+)", text)
            criteria.setdefault("liquidity", {})["relative_volume_gte"] = float(match.group(1)) if match else 2
        price_match = re.search(r"(?:price\s*)?(?:<|less than|under|below)\s*\$?\s*(\d+(?:\.\d+)?)", text)
        if price_match:
            criteria.setdefault("price", {})["max"] = float(price_match.group(1))
        price_match = re.search(r"(?:price\s*)?(?:>|more than|over|above)\s*\$?\s*(\d+(?:\.\d+)?)", text)
        if price_match:
            criteria.setdefault("price", {})["min"] = float(price_match.group(1))
        range_match = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:to|-|and)\s*\$?\s*(\d+(?:\.\d+)?)", text)
        if range_match and "price" in text:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            criteria["price"] = {"min": min(low, high), "max": max(low, high)}
        if any(phrase in text for phrase in ("low priced", "cheap", "penny stock")) and "price" not in criteria:
            criteria["price"] = {"relation": "under", "value": 10}
        if "above the 50 day moving average" in text or "above sma50" in text or "sma50" in text:
            criteria.setdefault("technical", {})["sma"] = {"period": 50, "relation": "above"}
        if "above the 200 day moving average" in text or "above sma200" in text:
            criteria.setdefault("technical", {})["sma"] = {"period": 200, "relation": "above"}

        requested_limit = _requested_limit(request_text)
        if requested_limit is not None:
            criteria["limit"] = requested_limit
        elif any(word in text for word in ("top", "best", "strongest")):
            criteria["limit"] = 5

        if any(word in text for word in ("strongest", "best", "top")):
            criteria["ranking"] = {"primary": "change_from_open", "direction": "desc"}

        if not criteria:
            task["open_questions"].append("No explicit Finviz criteria were inferred.")

        workflow["criteria"] = criteria
        task["objective"] = f"Finviz {workflow['mode']} request"
        task["constraints"].append("Use the selected Finviz tool and return a concise result set.")
        task["expected_output"] = "A Finviz result set or lookup based on the inferred mode."

    task["workflow"] = workflow
    return task


def _llm_interpret(request_text: str) -> dict[str, Any]:
    return chat_json(system=SYSTEM_PROMPT, user=request_text)


def _coerce_task(spec: Any, request_text: str) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("LLM response was not a JSON object")

    task = {
        "request": request_text,
        "objective": spec.get("objective") or request_text.splitlines()[0] if request_text else None,
        "constraints": spec.get("constraints") or [],
        "expected_output": spec.get("expected_output") or "",
        "assumptions": spec.get("assumptions") or [],
        "open_questions": spec.get("open_questions") or [],
        "workflow": spec.get("workflow") or {"domain": "generic", "tool": None, "mode": None, "criteria": {}},
    }

    if not isinstance(task["constraints"], list):
        task["constraints"] = [task["constraints"]]
    if not isinstance(task["assumptions"], list):
        task["assumptions"] = [task["assumptions"]]
    if not isinstance(task["open_questions"], list):
        task["open_questions"] = [task["open_questions"]]
    if not isinstance(task["workflow"], dict):
        task["workflow"] = {"domain": "generic", "tool": None, "mode": None, "criteria": {}}

    task["request"] = request_text
    return task


def normalize_request(request_text: str) -> dict:
    request_text = _clean_request_text(request_text)
    if not request_text:
        return _semantic_fallback("")

    try:
        llm_task = _coerce_task(_llm_interpret(request_text), request_text)
        if not llm_task.get("workflow"):
            raise ValueError("Missing workflow from LLM response")
        return llm_task
    except (LLMError, ValueError, json.JSONDecodeError):
        return _semantic_fallback(request_text)


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
