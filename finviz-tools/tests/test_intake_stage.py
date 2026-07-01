from shared.llm import LLMError

from ._stage_loader import load_stage

intake = load_stage("01_intake")


def test_fallback_produces_validated_task_with_no_open_questions():
    task = intake._validate_or_flag(
        intake._semantic_fallback("top 5 large cap energy stocks up at least 3% since the open")
    )
    workflow = task["workflow"]
    assert workflow["domain"] == "finviz"
    assert workflow["criteria"]["sector"] == "Energy"
    assert workflow["criteria"]["limit"] == 5
    assert task["open_questions"] == []


def test_normalize_request_falls_back_when_llm_unavailable(monkeypatch):
    def _raise(*args, **kwargs):
        raise LLMError("no endpoint configured")

    monkeypatch.setattr(intake, "_llm_interpret", _raise)
    task = intake.normalize_request("stocks priced <$10 and >$2")
    assert task["workflow"]["domain"] == "finviz"
    assert task["workflow"]["criteria"]["price"] == {"min": 2.0, "max": 10.0}


def test_invalid_llm_output_degrades_to_open_question_not_crash(monkeypatch):
    monkeypatch.setattr(intake, "_llm_interpret", lambda text: {"workflow": {"domain": "not-a-domain"}})
    task = intake.normalize_request("some request")
    assert any("DSL validation failed" in q for q in task["open_questions"])
