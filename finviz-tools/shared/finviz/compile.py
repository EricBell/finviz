"""Compile semantic Finviz criteria into screener filters."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .catalog import nearest_numeric_label, resolve_label
from .errors import FinvizInvalidFilterError

_MARKET_CAP_LABELS = {
    "mega": "Mega ($200bln and more)",
    "large": "Large ($10bln to $200bln)",
    "mid": "Mid ($2bln to $10bln)",
    "small": "Small ($300mln to $2bln)",
    "micro": "Micro ($50mln to $300mln)",
    "nano": "Nano (under $50mln)",
}


def _iter_values(value: Any) -> Iterable[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Iterable):
        return value
    return [value]


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

    for key, label in _MARKET_CAP_LABELS.items():
        if key in value:
            return resolve_label("Market Cap.", label)
    raise FinvizInvalidFilterError(f"Unknown market cap class: {market_cap!r}")


def _choice_for_price(price: Any) -> list[str]:
    if price is None:
        return []

    if isinstance(price, dict):
        # Range form: {"min": 2, "max": 10}
        if price.get("min") is not None or price.get("max") is not None:
            out: list[str] = []
            if price.get("min") is not None:
                out.append(nearest_numeric_label("Price $", float(price["min"]), "over"))
            if price.get("max") is not None:
                out.append(nearest_numeric_label("Price $", float(price["max"]), "under"))
            return out

        relation = str(price.get("relation") or price.get("op") or price.get("direction") or "").lower()
        value = price.get("value")
    else:
        relation = ""
        value = price

    if value is None:
        return []
    direction = "under" if relation in {"under", "below", "lte", "lteq", "le"} else "over"
    return [nearest_numeric_label("Price $", float(value), direction)]


def _choice_for_percent(group: str, amount: Any, *, relation: str = "over") -> str | None:
    if amount is None:
        return None
    try:
        value = float(amount)
    except (TypeError, ValueError) as exc:
        raise FinvizInvalidFilterError(f"Bad numeric value: {amount!r}") from exc
    direction = "over" if relation in {"over", "above", "gte", "gteq", "ge"} else "under"
    return nearest_numeric_label(group, value, direction)


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
        return resolve_label(group, f"Price above SMA{period}")
    if relation in {"below", "under", "bearish", "pb"}:
        return resolve_label(group, f"Price below SMA{period}")
    if relation in {"crossabove", "crossed_above", "pca"}:
        return resolve_label(group, f"Price crossed SMA{period} above")
    if relation in {"crossbelow", "crossed_below", "pcb"}:
        return resolve_label(group, f"Price crossed SMA{period} below")
    raise FinvizInvalidFilterError(f"Unsupported SMA relation: {relation!r}")


def _choice_for_relative_volume(value: Any) -> str | None:
    if value is None:
        return None
    return nearest_numeric_label("Relative Volume", float(value), "over")


def _choice_for_average_volume(value: Any) -> str | None:
    if value is None:
        return None
    return nearest_numeric_label("Average Volume", float(value), "over")


def compile_semantic_filters(criteria: dict) -> list[str]:
    filters: list[str] = []

    # Direct filters still work.
    direct = criteria.get("filters") or []
    filters.extend(str(item) for item in _iter_values(direct) if item)

    if isinstance(criteria.get("filter_groups"), dict):
        for group_name, selected in criteria["filter_groups"].items():
            for choice in _iter_values(selected):
                filters.append(resolve_label(group_name, str(choice)))

    if sector := criteria.get("sector"):
        filters.append(resolve_label("Sector", str(sector)))

    if industry := criteria.get("industry"):
        filters.append(resolve_label("Industry", str(industry)))

    if exchange := criteria.get("exchange"):
        filters.append(resolve_label("Exchange", str(exchange)))

    if index := criteria.get("index"):
        filters.append(resolve_label("Index", str(index)))

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
            filters.append(_choice_for_relative_volume(liquidity["relative_volume_gte"]))
        if "average_volume_gte" in liquidity:
            filters.append(_choice_for_average_volume(liquidity["average_volume_gte"]))

    technical = criteria.get("technical") or {}
    if isinstance(technical, dict) and technical.get("sma"):
        filters.append(_choice_for_sma(technical["sma"]))

    if criteria.get("rvol") is not None:
        filters.append(_choice_for_relative_volume(criteria["rvol"]))

    if criteria.get("gap_up_gte") is not None:
        filters.append(_choice_for_percent("Gap", criteria["gap_up_gte"]))

    if criteria.get("change_from_open_gte") is not None:
        filters.append(_choice_for_percent("Change from Open", criteria["change_from_open_gte"]))

    return list(dict.fromkeys(f for f in filters if f))
