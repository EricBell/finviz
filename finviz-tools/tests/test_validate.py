import pytest

from shared.finviz.errors import FinvizInvalidFilterError
from shared.finviz.validate import validate_task


def test_valid_task_passes_and_coerces_limit():
    task = {
        "workflow": {
            "domain": "finviz",
            "tool": "finviz.screen",
            "criteria": {"price": {"min": 2, "max": 10}, "limit": "5"},
        }
    }
    validated = validate_task(task)
    assert validated["workflow"]["criteria"]["limit"] == 5


def test_invalid_domain_raises():
    task = {"workflow": {"domain": "bogus", "tool": "finviz.screen", "criteria": {}}}
    with pytest.raises(FinvizInvalidFilterError):
        validate_task(task)


def test_screen_tool_requires_criteria():
    task = {"workflow": {"domain": "finviz", "tool": "finviz.screen"}}
    with pytest.raises(FinvizInvalidFilterError):
        validate_task(task)


def test_price_min_may_not_exceed_max():
    task = {
        "workflow": {
            "domain": "finviz",
            "tool": "finviz.screen",
            "criteria": {"price": {"min": 10, "max": 2}},
        }
    }
    with pytest.raises(FinvizInvalidFilterError):
        validate_task(task)


def test_price_min_and_max_may_coexist():
    task = {
        "workflow": {
            "domain": "finviz",
            "tool": "finviz.screen",
            "criteria": {"price": {"min": 2, "max": 10}},
        }
    }
    validate_task(task)  # should not raise


def test_non_integer_limit_raises():
    task = {
        "workflow": {
            "domain": "finviz",
            "tool": "finviz.screen",
            "criteria": {"limit": "five"},
        }
    }
    with pytest.raises(FinvizInvalidFilterError):
        validate_task(task)


def test_missing_workflow_raises():
    with pytest.raises(FinvizInvalidFilterError):
        validate_task({})
