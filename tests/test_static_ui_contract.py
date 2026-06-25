from pathlib import Path


STATIC_APP = Path("app/static/app.js")


def test_ui_uses_safe_text_helpers_instead_of_raw_api_inner_html():
    script = STATIC_APP.read_text(encoding="utf-8")

    assert "function escapeHtml" in script
    assert "escapeHtml(data.case_id)" in script
    assert "${data.case_id}" not in script
    assert "item.redacted_snippet}</span>" not in script
