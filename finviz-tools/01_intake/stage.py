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
    "rvol",
    "relative volume",
    "moving average",
    "sma",
    "breakout",
    "bullish",
    "momentum",
    "liquidity",
    "penny",
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


def _market_cap_filters(text: str) -> tuple[list[str], list[str]]:
    lowered = text.lower()
    filters: list[str] = []
    assumptions: list[str] = []

    exact_map = [
        ("mega cap", "cap_mega", "Interpreted 'mega cap' as Finviz cap_mega."),
        ("large cap", "cap_large", "Interpreted 'large cap' as Finviz cap_large."),
        ("mid cap", "cap_mid", "Interpreted 'mid cap' as Finviz cap_mid."),
        ("small cap", "cap_small", "Interpreted 'small cap' as Finviz cap_small."),
        ("micro cap", "cap_micro", "Interpreted 'micro cap' as Finviz cap_micro."),
        ("nano cap", "cap_nano", "Interpreted 'nano cap' as Finviz cap_nano."),
    ]
    has_cap_context = "market cap" in lowered or "marketcap" in lowered or any(phrase in lowered for phrase, _, _ in exact_map)
    for phrase, tag, note in exact_map:
        if phrase in lowered:
            filters.append(tag)
            assumptions.append(note)
            break

    def _value_to_millions(value: float, unit: str | None) -> float:
        unit = (unit or "").lower()
        if unit in {"b", "bn", "billion"}:
            return value * 1000.0
        if unit in {"k", "thousand"}:
            return value / 1000.0
        return value

    def _under_filter(millions: float) -> str:
        if millions <= 50:
            return "cap_nano"
        if millions <= 300:
            return "cap_microunder"
        if millions <= 2000:
            return "cap_smallunder"
        if millions <= 10000:
            return "cap_midunder"
        return "cap_largeunder"

    def _over_filter(millions: float) -> str:
        if millions >= 10000:
            return "cap_largeover"
        if millions >= 2000:
            return "cap_midover"
        if millions >= 300:
            return "cap_smallover"
        return "cap_microover"

    if has_cap_context:
        patterns = [
            r"\b(?P<direction>under|below|less than|sub|over|above|greater than)\s+\$?\s*(?P<value>[\d,.]+)\s*(?P<unit>bn|billion|b|mm|million|m|k|thousand)?\s*(?:market cap|cap)?",
            r"(?:market cap|cap)\s*(?P<direction>under|below|less than|sub|over|above|greater than)\s+\$?\s*(?P<value>[\d,.]+)\s*(?P<unit>bn|billion|b|mm|million|m|k|thousand)?",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if not match:
                continue
            direction = match.group("direction")
            value = float(match.group("value").replace(",", ""))
            millions = _value_to_millions(value, match.group("unit"))
            filters.append(_under_filter(millions) if direction in {"under", "below", "less than", "sub"} else _over_filter(millions))
            assumptions.append(f"Interpreted market cap {direction} {match.group('value')} as a Finviz market cap filter.")
            break

    return list(dict.fromkeys(filters)), assumptions


def _price_filters(text: str) -> tuple[list[str], list[str]]:
    lowered = text.lower()
    filters: list[str] = []
    assumptions: list[str] = []

    def _price_tag(direction: str, value: float) -> str:
        thresholds = [1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 40, 50]
        for threshold in thresholds:
            if direction == "under" and value <= threshold:
                return f"sh_price_u{int(threshold) if float(threshold).is_integer() else threshold}"
            if direction == "over" and value <= threshold:
                return f"sh_price_o{int(threshold) if float(threshold).is_integer() else threshold}"
        return "sh_price_u50" if direction == "under" else "sh_price_o50"

    if any(phrase in lowered for phrase in ("low priced", "cheap", "penny stock")):
        filters.append("sh_price_u10")
        assumptions.append("Interpreted low-priced language as under $10.")

    if "moving average" not in lowered and "sma" not in lowered:
        match = re.search(r"\b(?P<direction>under|below|less than|sub|over|above|greater than)\s+\$?\s*(?P<value>[\d.]+)", lowered)
        if match:
            direction = match.group("direction")
            value = float(match.group("value"))
            filters.append(_price_tag(direction, value))
            assumptions.append(f"Interpreted price {direction} {match.group('value')} as a Finviz price filter.")

    return list(dict.fromkeys(filters)), assumptions


def _relative_volume_filters(text: str) -> tuple[list[str], list[str]]:
    lowered = text.lower()
    filters: list[str] = []
    assumptions: list[str] = []

    match = re.search(r"\b(?:rvol|rv|relative volume|rel volume|rel vol)\s*(?:is|above|over|>|>=)?\s*([\d.]+)", lowered)
    if match:
        value = float(match.group(1))
        thresholds = [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5, 10]
        tag = None
        for threshold in thresholds:
            if value <= threshold:
                tag = f"sh_relvol_o{threshold}"
                break
        if tag is None:
            tag = "sh_relvol_o10"
        filters.append(tag)
        assumptions.append(f"Interpreted relative volume > {match.group(1)} as a Finviz relative volume filter.")
    elif any(phrase in lowered for phrase in ("relative volume", "rvol", "high volume", "unusual volume")):
        filters.append("sh_relvol_o2")
        assumptions.append("Interpreted volume strength as relative volume > 2.")

    if any(phrase in lowered for phrase in ("liquidity", "liquid", "tradable", "active volume")):
        filters.append("sh_avgvol_o500")
        assumptions.append("Interpreted liquidity request as average volume over 500K.")

    return list(dict.fromkeys(filters)), assumptions


def _sma_filters(text: str) -> tuple[list[str], list[str]]:
    lowered = text.lower()
    filters: list[str] = []
    assumptions: list[str] = []

    def _period_aliases(period: int) -> list[str]:
        return [
            f"sma{period}",
            f"sma {period}",
            f"{period}-day moving average",
            f"{period} day moving average",
            f"{period} day sma",
            f"{period}dma",
        ]

    def _tag(period: int, suffix: str) -> str:
        return f"ta_sma{period}_{suffix}"

    for period in (20, 50, 200):
        if not any(alias in lowered for alias in _period_aliases(period)):
            continue
        if any(phrase in lowered for phrase in ("crossed above", "cross above", "broke above", "break above")):
            filters.append(_tag(period, "pca"))
            assumptions.append(f"Interpreted SMA{period} breakout as price crossed above the moving average.")
        elif any(phrase in lowered for phrase in ("crossed below", "cross below", "broke below", "break below")):
            filters.append(_tag(period, "pcb"))
            assumptions.append(f"Interpreted SMA{period} weakness as price crossed below the moving average.")
        elif any(phrase in lowered for phrase in ("above", "over", "bullish")) and not any(
            phrase in lowered for phrase in ("below", "under")
        ):
            filters.append(_tag(period, "pa"))
            assumptions.append(f"Interpreted 'above SMA{period}' as price above the moving average.")
        elif any(phrase in lowered for phrase in ("below", "under")):
            filters.append(_tag(period, "pb"))
            assumptions.append(f"Interpreted 'below SMA{period}' as price below the moving average.")

    if any(phrase in lowered for phrase in ("breakout", "momentum", "bullish")) and not filters:
        filters.extend(["ta_sma20_pa", "sh_relvol_o2"])
        assumptions.append("Interpreted momentum/breakout language as price above SMA20 with relative volume > 2.")

    return list(dict.fromkeys(filters)), assumptions


def _screen_criteria(text: str) -> tuple[dict[str, Any], list[str], list[str]]:
    criteria: dict[str, Any] = {}
    assumptions: list[str] = []
    open_questions: list[str] = []

    filters: list[str] = []
    cap_filters, cap_assumptions = _market_cap_filters(text)
    gap_filters, gap_assumptions = _gap_filter(text)
    price_filters, price_assumptions = _price_filters(text)
    rvol_filters, rvol_assumptions = _relative_volume_filters(text)
    sma_filters, sma_assumptions = _sma_filters(text)

    filters.extend(cap_filters)
    filters.extend(gap_filters)
    filters.extend(price_filters)
    filters.extend(rvol_filters)
    filters.extend(sma_filters)

    assumptions.extend(cap_assumptions)
    assumptions.extend(gap_assumptions)
    assumptions.extend(price_assumptions)
    assumptions.extend(rvol_assumptions)
    assumptions.extend(sma_assumptions)

    lowered = text.lower()
    order = ""
    if any(word in lowered for word in ("strongest", "best", "most bullish", "highest momentum", "most active")):
        order = "-change"
        assumptions.append("Used price change as a proxy for 'strongest'.")
    elif any(word in lowered for word in ("volume", "liquidity", "rvol", "relative volume")):
        order = "-volume"
        assumptions.append("Used volume as a proxy for strength.")

    requested_limit = _requested_limit(text)
    if requested_limit is not None:
        limit = requested_limit
    elif any(word in lowered for word in ("strongest", "top", "best", "highest")):
        limit = 5
    else:
        limit = 10

    criteria["filters"] = list(dict.fromkeys(filters))
    criteria["rows"] = limit
    if order:
        criteria["order"] = order
    criteria["table"] = "Overview"
    criteria["request_method"] = "sequential"
    criteria["sort_hint"] = ["gap", "relative volume", "price change", "liquidity"]

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
