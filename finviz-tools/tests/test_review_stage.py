from ._stage_loader import load_stage

review = load_stage("04_review")


def _run_review(tmp_path, monkeypatch, draft_text):
    intake_dir = tmp_path / "01_intake" / "output"
    plan_dir = tmp_path / "02_plan" / "output"
    exec_dir = tmp_path / "03_execute" / "output"
    output_dir = tmp_path / "04_review" / "output"
    for d in (intake_dir, plan_dir, exec_dir, output_dir):
        d.mkdir(parents=True)

    (intake_dir / "task.json").write_text("{}", encoding="utf-8")
    (plan_dir / "plan.json").write_text("{}", encoding="utf-8")
    (exec_dir / "draft.md").write_text(draft_text, encoding="utf-8")

    monkeypatch.setattr(review, "INTAKE_DIR", intake_dir)
    monkeypatch.setattr(review, "PLAN_DIR", plan_dir)
    monkeypatch.setattr(review, "EXEC_DIR", exec_dir)
    monkeypatch.setattr(review, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(review, "FINAL_MD", output_dir / "final.md")
    monkeypatch.setattr(review, "REVIEW_MD", output_dir / "review-notes.md")

    review.main()
    return output_dir


def test_empty_result_writes_empty_final_md_with_note(tmp_path, monkeypatch):
    output_dir = _run_review(tmp_path, monkeypatch, "# Draft Output\n\n## Result\nNo results.\n")
    assert (output_dir / "final.md").read_text(encoding="utf-8") == ""
    assert "No results found" in (output_dir / "review-notes.md").read_text(encoding="utf-8")


def test_nonempty_result_is_wrapped_in_final_output(tmp_path, monkeypatch):
    output_dir = _run_review(tmp_path, monkeypatch, "# Draft Output\n\nRows: 2\n\n| Ticker |\n| --- |\n| A |\n")
    final = (output_dir / "final.md").read_text(encoding="utf-8")
    assert "# Final Output" in final
    assert "| A |" in final
