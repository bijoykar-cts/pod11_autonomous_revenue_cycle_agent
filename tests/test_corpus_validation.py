from app.corpus.loader import load_default_corpus
from app.corpus.validator import validate_code


def test_known_cm_code_is_valid():
    corpus = load_default_corpus()

    result = validate_code(corpus, "I10", "ICD-10-CM")

    assert result.validation_status == "valid"
    assert result.description == "Essential (primary) hypertension"


def test_known_pcs_code_is_valid():
    corpus = load_default_corpus()

    result = validate_code(corpus, "0FT44ZZ", "ICD-10-PCS")

    assert result.validation_status == "valid"
    assert result.description


def test_unknown_code_is_not_in_configured_corpus():
    corpus = load_default_corpus()

    result = validate_code(corpus, "ZZZ999", "ICD-10-CM")

    assert result.validation_status == "not_in_configured_corpus"
    assert result.description == ""


def test_corpus_version_is_loaded_from_manifest():
    corpus = load_default_corpus()

    assert corpus.version == "configured-default"
    assert corpus.record_count >= 1
