import shared.finviz

from ._stage_loader import load_stage

execute = load_stage("03_execute")

SAMPLE_ROWS = [
    {"Ticker": "A", "Change": "1%"},
    {"Ticker": "B", "Change": "5%"},
    {"Ticker": "C", "Change": "3%"},
    {"Ticker": "D", "Change": "9%"},
    {"Ticker": "E", "Change": "2%"},
]


def _task(criteria):
    return {"objective": "test", "workflow": {"domain": "finviz", "tool": "finviz.screen", "criteria": criteria}}


def test_limit_is_respected_without_ranking(monkeypatch, tmp_path):
    monkeypatch.setattr(shared.finviz, "screen", lambda criteria: list(SAMPLE_ROWS))
    monkeypatch.setattr(execute, "ARTIFACTS_DIR", tmp_path)

    draft = execute._run_finviz(_task({"sector": "Energy", "limit": 2}), {"steps": []})
    assert "Rows: 2" in draft


def test_ranking_picks_true_top_n_not_a_pre_truncated_sample(monkeypatch, tmp_path):
    seen_criteria = {}

    def fake_screen(criteria):
        seen_criteria.update(criteria)
        return list(SAMPLE_ROWS)

    monkeypatch.setattr(shared.finviz, "screen", fake_screen)
    monkeypatch.setattr(execute, "ARTIFACTS_DIR", tmp_path)

    criteria = {"sector": "Energy", "limit": 2, "ranking": {"primary": "change", "direction": "desc"}}
    draft = execute._run_finviz(_task(criteria), {"steps": []})

    # The fetch must not be capped by `limit` when ranking is requested.
    assert "limit" not in seen_criteria

    # Top 2 by Change (desc) out of the full sample are D (9%) and B (5%).
    assert "Rows: 2" in draft
    assert draft.index("| D ") < draft.index("| B ")
    assert "| A " not in draft


def test_unresolvable_criteria_produces_readable_draft_not_a_crash(monkeypatch, tmp_path):
    monkeypatch.setattr(execute, "ARTIFACTS_DIR", tmp_path)
    draft = execute._run_finviz(_task({"sector": "NotARealSector"}), {"steps": []})
    assert "Could not compile the requested criteria" in draft
