"""Helpers for turning higher-level criteria into Finviz screener inputs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .config import DEFAULT_ORDER, DEFAULT_TABLE
from .errors import FinvizInvalidFilterError


def normalize_query(request: Any) -> dict:
    """Normalize a raw request into a task dictionary.

    This intentionally stays lightweight: it preserves the original request and
    standardizes a few obvious container fields.
    """

    if isinstance(request, dict):
        data = dict(request)
        data.setdefault("request", request.get("request", ""))
    else:
        data = {"request": str(request)}

    for key in ("constraints", "assumptions", "open_questions"):
        value = data.get(key)
        if value is None:
            data[key] = []
        elif not isinstance(value, list):
            data[key] = [value]

    return data


def get_filter_options(reload: bool = False) -> dict:
    """Return the nested Finviz filter dictionary.

    If reload is True, force a fresh fetch from Finviz; otherwise prefer the
    cached filters.json when available.
    """

    from finviz.screener import Screener

    return Screener.load_filter_dict(reload=not reload)


def _iter_values(value: Any) -> Iterable[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Iterable):
        return value
    return [value]


def build_filters(criteria: dict) -> list[str]:
    """Build a flat list of Finviz filter tags from a criteria dict.

    Supported inputs:
    - ``filters``: direct Finviz filter tags
    - ``filter_groups``: mapping of Finviz category name -> selected option(s)
    """

    filters: list[str] = []

    direct_filters = criteria.get("filters") or []
    for item in _iter_values(direct_filters):
        if item:
            filters.append(str(item))

    grouped = criteria.get("filter_groups") or {}
    if grouped:
        options = get_filter_options(reload=criteria.get("reload_filters", False))
        for group_name, selected in grouped.items():
            group = options.get(group_name)
            if group is None:
                raise FinvizInvalidFilterError(f"Unknown filter group: {group_name}")
            for choice in _iter_values(selected):
                if choice not in group:
                    raise FinvizInvalidFilterError(
                        f"Unknown filter choice {choice!r} in group {group_name!r}"
                    )
                filters.append(group[choice])

    # De-duplicate while preserving order.
    return list(dict.fromkeys(filters))


def describe_filters(filters: list[str]) -> dict[str, str]:
    """Return a mapping of filter tag -> human-readable label."""

    reverse: dict[str, str] = {}
    for group_name, group in get_filter_options(reload=False).items():
        for label, tag in group.items():
            reverse[tag] = f"{group_name}: {label}"

    return {flt: reverse.get(flt, flt) for flt in filters}


def build_screener_kwargs(criteria: dict) -> dict:
    """Translate a criteria dictionary into Screener keyword arguments."""

    return {
        "tickers": criteria.get("tickers"),
        "filters": build_filters(criteria),
        "rows": criteria.get("rows"),
        "order": criteria.get("order", DEFAULT_ORDER),
        "signal": criteria.get("signal", ""),
        "table": criteria.get("table", DEFAULT_TABLE),
        "custom": criteria.get("custom"),
        "request_method": criteria.get("request_method", "sequential"),
    }
