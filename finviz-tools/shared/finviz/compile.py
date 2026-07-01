"""Compile semantic Finviz criteria into screener filters."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import re

from .errors import FinvizInvalidFilterError


def _iter_values(value: Any) -> Iterable[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Iterable):
        return value
    return [value]


def _get_filter_options() -> dict:
    from .filters import get_filter_options

    return get_filter_options(reload=False)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _find_choice(group_name: str, predicate) -> str:
    options = _get_filter_options()
    target = _norm(group_name)

    exact = None
    prefix = None
    for key, value in options.items():
        key_norm = _norm(key)
        if key_norm == target:
            exact = value
            break
        if prefix is None and (key_norm.startswith(target) or target.startswith(key_norm)):
            prefix = value

    group = exact or prefix
    if not group:
        raise FinvizInvalidFilterError(f"Unknown filter group: {group_name}")
    for label, tag in group.items():
        if predicate(label):
            return tag
    raise FinvizInvalidFilterError(f"No choice found in {group_name!r}")


def _choice_contains(group_name: str, needle: str) -> str:
    needle = needle.lower()
    return _find_choice(group_name, lambda label: needle in label.lower())


def _choice_exact(group_name: str, label: str) -> str:
    target = label.strip().lower()
    return _find_choice(group_name, lambda choice: choice.strip().lower() == target)


def _choice_for_market_cap(market_cap: Any) -> str | None:
    if market_cap is None:
        return None
    if isinstance(market_cap, str):
        value = market_cap.lower().replace("cap", "").strip()
    elif isinstance(market_cap, dict):
        value = str(
            market_cap.get("class")
            or market_cap.get("value")
            or market_cap.get("size")
            or market_cap.get("relation")
            or ""
        ).lower()
    else:
        value = str(market_cap).lower()

    mapping = {
        "mega": "Mega",
        "large": "Large",
        "mid": "Mid",
        "small": "Small",
        "micro": "Micro",
        "nano": "Nano",
    }
    for key, label in mapping.items():
        if key in value:
            return _choice_contains("Market Cap", label)
    raise FinvizInvalidFilterError(f"Unknown market cap class: {market_cap!r}")


def _choice_for_price(price: Any) -> list[str]:
    if price is None:
        return []

    if isinstance(price, dict):
        # Range form: {"min": 2, "max": 10}
        if price.get("min") is not None or price.get("max") is not None:
            out: list[str] = []
            if price.get("min") is not None:
                out.append(_choice_contains("Price $", f"Over ${int(float(price['min']))}"))
            if price.get("max") is not None:
                out.append(_choice_contains("Price $", f"Under ${int(float(price['max']))}"))
            return out

        relation = str(price.get("relation") or price.get("op") or price.get("direction") or "").lower()
        value = price.get("value")
    else:
        relation = ""
        value = price

    if value is None:
        return []
    relation = relation or "over"
    return [_choice_contains("Price $", f"{relation.title()} ${int(float(value))}")]


def _choice_for_percent(group: str, amount: Any, *, relation: str = "over") -> str | None:
    if amount is None:
        return None
    try:
        value = int(round(float(amount)))
    except (TypeError, ValueError) as exc:
        raise FinvizInvalidFilterError(f"Bad numeric value: {amount!r}") from exc
    label = f"Up {value}%" if relation in {"over", "above", "gte", "gteq", "ge"} else f"Down {value}%"
    return _choice_exact(group, label)


def _choice_for_sma(sma: Any) -> str | None:
    if sma is None:
        return None
    if not isinstance(sma, dict):
        raise FinvizInvalidFilterError(f"Bad SMA spec: {sma!r}")
    period = int(sma.get("period") or sma.get("days") or 0)
    relation = str(sma.get("relation") or sma.get("direction") or "above").lower()
    if period not in {20, 50, 200}:
        raise FinvizInvalidFilterError(f"Unsupported SMA period: {period!r}")

    group = f"{period}-Day Simple Moving Average"
    if relation in {"above", "over", "bullish", "pa"}:
        return _choice_exact(group, f"Price above SMA{period}")
    if relation in {"below", "under", "bearish", "pb"}:
        return _choice_exact(group, f"Price below SMA{period}")
    if relation in {"crossabove", "crossed_above", "pca"}:
        return _choice_exact(group, f"Price crossed SMA{period} above")
    if relation in {"crossbelow", "crossed_below", "pcb"}:
        return _choice_exact(group, f"Price crossed SMA{period} below")
    raise FinvizInvalidFilterError(f"Unsupported SMA relation: {relation!r}")


def compile_semantic_filters(criteria: dict) -> list[str]:
    filters: list[str] = []

    # Direct filters still work.
    direct = criteria.get("filters") or []
    filters.extend(str(item) for item in _iter_values(direct) if item)

    if isinstance(criteria.get("filter_groups"), dict):
        for group_name, selected in criteria["filter_groups"].items():
            for choice in _iter_values(selected):
                filters.append(_choice_exact(group_name, str(choice)))

    if sector := criteria.get("sector"):
        filters.append(_choice_exact("Sector", str(sector)))

    if industry := criteria.get("industry"):
        filters.append(_choice_exact("Industry", str(industry)))

    if exchange := criteria.get("exchange"):
        filters.append(_choice_exact("Exchange", str(exchange)))

    if index := criteria.get("index"):
        filters.append(_choice_exact("Index", str(index)))

    if market_cap := criteria.get("market_cap"):
        filters.append(_choice_for_market_cap(market_cap))

    if price := criteria.get("price"):
        filters.extend(_choice_for_price(price))

    performance = criteria.get("performance") or {}
    if isinstance(performance, dict):
        if "gap_up_gte" in performance:
            filters.append(_choice_for_percent("Gap", performance["gap_up_gte"]))
        if "change_from_open_gte" in performance:
            filters.append(_choice_for_percent("Change from Open", performance["change_from_open_gte"]))
        if "change_gte" in performance:
            filters.append(_choice_for_percent("Change", performance["change_gte"]))

    liquidity = criteria.get("liquidity") or {}
    if isinstance(liquidity, dict):
        if "relative_volume_gte" in liquidity:
            value = float(liquidity["relative_volume_gte"])
            if value >= 10:
                label = "Over 10"
            elif value >= 5:
                label = "Over 5"
            elif value >= 3:
                label = "Over 3"
            elif value >= 2:
                label = "Over 2"
            elif value >= 1.5:
                label = "Over 1.5"
            elif value >= 1:
                label = "Over 1"
            elif value >= 0.75:
                label = "Over 0.75"
            elif value >= 0.5:
                label = "Over 0.5"
            elif value >= 0.25:
                label = "Over 0.25"
            else:
                label = "Over 0.25"
            filters.append(_choice_exact("Relative Volume", label))
        if "average_volume_gte" in liquidity:
            amount = liquidity["average_volume_gte"]
            amount = float(amount)
            if amount < 1:
                amount = amount * 1000_000
            if amount >= 1_000_000:
                label = "Over 1M"
            elif amount >= 500_000:
                label = "Over 500K"
            elif amount >= 300_000:
                label = "Over 300K"
            elif amount >= 200_000:
                label = "Over 200K"
            elif amount >= 100_000:
                label = "Over 100K"
            else:
                label = "Over 50K"
            filters.append(_choice_exact("Average Volume", label))

    technical = criteria.get("technical") or {}
    if isinstance(technical, dict) and technical.get("sma"):
        filters.append(_choice_for_sma(technical["sma"]))

    if criteria.get("rvol") is not None:
        filters.append(_choice_exact("Relative Volume", f"Over {int(float(criteria['rvol']))}"))

    if criteria.get("gap_up_gte") is not None:
        filters.append(_choice_for_percent("Gap", criteria["gap_up_gte"]))

    if criteria.get("change_from_open_gte") is not None:
        filters.append(_choice_for_percent("Change from Open", criteria["change_from_open_gte"]))

    return [flt for flt in dict.fromkeys(f for f in filters if f)]
