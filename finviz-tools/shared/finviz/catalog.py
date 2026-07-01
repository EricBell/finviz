"""Catalog lookups over finviz/filters.json.

This module is the single place that knows how to fuzzy-match category/group
names and option labels, and how to pick the nearest numeric-threshold label
(e.g. "Over 500K", "Under $10", "Up 7%") for an arbitrary requested value.
compile.py should not hardcode group names, labels, or numeric ladders itself;
it should call through here.
"""

from __future__ import annotations

import re
from typing import Literal

from .errors import FinvizInvalidFilterError

_catalog_cache: dict | None = None

_UNIT_MULTIPLIERS = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}

# Matches labels like: "Over $10", "Under 500K", "Up 7%", "Down 1M", "Over 1.5"
_NUMERIC_LABEL_RE = re.compile(
    r"^(?P<dir>Over|Under|Up|Down)\s*\$?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[KMB%]?)$",
    re.IGNORECASE,
)


def _load_catalog() -> dict:
    global _catalog_cache
    if _catalog_cache is None:
        from finviz.screener import Screener

        _catalog_cache = Screener.load_filter_dict(reload=True)
    return _catalog_cache


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def resolve_group(name: str) -> tuple[str, dict[str, str]]:
    """Resolve a (possibly loosely-named) filter group to its canonical name and options."""

    catalog = _load_catalog()
    target = _norm(name)

    exact_key = None
    prefix_key = None
    for key in catalog:
        key_norm = _norm(key)
        if key_norm == target:
            exact_key = key
            break
        if prefix_key is None and (key_norm.startswith(target) or target.startswith(key_norm)):
            prefix_key = key

    canonical = exact_key or prefix_key
    if canonical is None:
        raise FinvizInvalidFilterError(f"Unknown filter group: {name!r}")
    return canonical, catalog[canonical]


def resolve_label(group: str, label: str) -> str:
    """Resolve a label within a group to its Finviz filter tag."""

    canonical, options = resolve_group(group)
    target = label.strip().lower()

    for choice, tag in options.items():
        if choice.strip().lower() == target:
            return tag

    for choice, tag in options.items():
        if target in choice.strip().lower():
            return tag

    raise FinvizInvalidFilterError(
        f"No option matching {label!r} in group {canonical!r}. "
        f"Available: {', '.join(list(options)[:10])}"
    )


def _parse_numeric_label(label: str) -> tuple[str, float] | None:
    match = _NUMERIC_LABEL_RE.match(label.strip())
    if not match:
        return None

    direction = match.group("dir").lower()
    value = float(match.group("value"))
    unit = match.group("unit").lower()
    if unit in _UNIT_MULTIPLIERS:
        value *= _UNIT_MULTIPLIERS[unit]

    bucket = "over" if direction in {"over", "up"} else "under"
    return bucket, value


def _normalize_requested_value(value: float, sample_labels: list[str]) -> float:
    """Scale a raw requested value (e.g. 0.5 meaning 500K) to match label units."""

    if any(re.search(r"[KMB]$", lbl.strip(), re.IGNORECASE) for lbl in sample_labels) and 0 < value < 1:
        return value * 1_000_000
    return value


def nearest_numeric_label(
    group: str,
    value: float,
    direction: Literal["over", "under"],
) -> str:
    """Find the group's numeric-threshold label nearest to `value` in the given direction.

    "over" (satisfying an "at least value" request) picks the smallest
    available threshold that is >= value, so every stock the filter passes
    truly satisfies the request (no false positives below value); if no
    threshold reaches that high, the largest available threshold is used as
    a best effort. "under" (satisfying an "at most value" request) is the
    mirror image: the largest threshold <= value, or the smallest available
    threshold if none qualifies.
    """

    canonical, options = resolve_group(group)
    candidates: list[tuple[float, str]] = []
    for label, tag in options.items():
        parsed = _parse_numeric_label(label)
        if parsed is None:
            continue
        bucket, threshold = parsed
        if bucket == direction:
            candidates.append((threshold, tag))

    if not candidates:
        raise FinvizInvalidFilterError(f"Group {canonical!r} has no {direction!r} numeric labels")

    value = _normalize_requested_value(value, list(options))
    candidates.sort(key=lambda item: item[0])

    if direction == "over":
        # Tightest threshold that still guarantees the "at least value" request.
        eligible = [c for c in candidates if c[0] >= value]
        chosen = min(eligible, key=lambda item: item[0]) if eligible else max(candidates, key=lambda item: item[0])
    else:
        eligible = [c for c in candidates if c[0] <= value]
        chosen = max(eligible, key=lambda item: item[0]) if eligible else min(candidates, key=lambda item: item[0])

    return chosen[1]


def list_groups() -> list[str]:
    return list(_load_catalog())


def list_labels(group: str) -> dict[str, str]:
    _, options = resolve_group(group)
    return options


def full_catalog() -> dict:
    """Return the raw group -> {label: tag} catalog."""

    return _load_catalog()
