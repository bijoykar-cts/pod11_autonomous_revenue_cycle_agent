from app.corpus.loader import load_default_corpus
from app.orchestration.coding_pipeline import CodingPipeline


def run_pipeline(note_text: str):
    pipeline = CodingPipeline(corpus=load_default_corpus())
    return pipeline.run(
        case_id="pipeline-test",
        note_text=note_text,
        include_debug=False,
        persist_note=False,
    )


def test_negated_condition_is_not_accepted():
    result = run_pipeline("Patient denies pneumonia. Hypertension is controlled.")

    assert any(flag.type == "negated_condition" for flag in result.review_flags)
    assert all(code.code != "J18.9" or code.status != "accepted" for code in result.diagnosis_codes)


def test_ruled_out_condition_is_flagged():
    result = run_pipeline("Pneumonia was ruled out after clear chest x-ray.")

    assert any(flag.type == "ruled_out_condition" for flag in result.review_flags)
    assert all(code.status != "accepted" for code in result.diagnosis_codes)


def test_history_of_condition_requires_review():
    result = run_pipeline("History of pneumonia documented. No active infection today.")

    assert any(flag.type == "history_of_condition" for flag in result.review_flags)
    assert all(code.code != "J18.9" or code.status != "accepted" for code in result.diagnosis_codes)


def test_specificity_gap_returns_needs_documentation():
    result = run_pipeline("Patient has diabetes.")

    assert any(code.status == "needs_documentation" for code in result.diagnosis_codes)
    assert any(flag.type == "specificity_gap" for flag in result.review_flags)


def test_all_checks_pass_allows_auto_accept():
    result = run_pipeline("Patient has essential hypertension.")

    assert any(code.code == "I10" and code.status == "accepted" for code in result.diagnosis_codes)


def test_cm_pcs_conflict_suppresses_lower_confidence_side():
    result = run_pipeline(
        "Laparoscopic cholecystectomy performed. Essential hypertension also documented."
    )

    assert result.procedure_codes
    assert all(code.status != "accepted" for code in result.diagnosis_codes)
    assert any(flag.type == "conflict_suppressed" for flag in result.review_flags)
