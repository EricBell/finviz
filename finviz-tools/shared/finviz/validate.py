"""Validation for the intake DSL task shape."""

from __future__ import annotations

from typing import Any

from .errors import FinvizInvalidFilterError

VALID_DOMAINS = {"finviz", "generic"}


def _coerce_limit(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise FinvizInvalidFilterError(f"limit must be an integer, got {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    raise FinvizInvalidFilterError(f"limit must be an integer, got {value!r}")


def validate_task(task: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a task dict produced by intake.

    Raises FinvizInvalidFilterError on malformed workflow/criteria shapes.
    Returns the same task with `limit` coerced to int where present.
    """

    workflow = task.get("workflow")
    if not isinstance(workflow, dict):
        raise FinvizInvalidFilterError("task.workflow must be an object")

    domain = workflow.get("domain")
    if domain is not None and domain not in VALID_DOMAINS:
        raise FinvizInvalidFilterError(f"workflow.domain must be one of {sorted(VALID_DOMAINS)}, got {domain!r}")

    tool = workflow.get("tool")
    criteria = workflow.get("criteria")

    if tool == "finviz.screen":
        if criteria is None:
            raise FinvizInvalidFilterError("workflow.criteria is required when tool is finviz.screen")
        if not isinstance(criteria, dict):
            raise FinvizInvalidFilterError("workflow.criteria must be an object")

    if isinstance(criteria, dict):
        price = criteria.get("price")
        if isinstance(price, dict) and price.get("min") is not None and price.get("max") is not None:
            try:
                if float(price["min"]) > float(price["max"]):
                    raise FinvizInvalidFilterError(
                        f"price.min ({price['min']!r}) must not exceed price.max ({price['max']!r})"
                    )
            except (TypeError, ValueError) as exc:
                raise FinvizInvalidFilterError(f"price.min/max must be numeric: {price!r}") from exc

        if "limit" in criteria:
            criteria["limit"] = _coerce_limit(criteria["limit"])

    return task
