from pathlib import Path

from view_xy_server import _json_for_inline_script, build_html


def test_inline_json_cannot_close_script_tag() -> None:
    payload = [{"naam": "</script><script>alert(1)</script>"}]
    encoded = _json_for_inline_script(payload)

    assert "</script>" not in encoded
    assert "\\u003c/script\\u003e" in encoded


def test_build_html_keeps_untrusted_data_inside_script(tmp_path: Path) -> None:
    template = tmp_path / "template.html"
    template.write_text(
        "<script>const data = __INJECT_DATA_VO__;</script>",
        encoding="utf-8",
    )

    html = build_html(template, [{"naam": "</script><h1>owned</h1>"}], [], [], [])

    assert html.count("</script>") == 1
    assert "<h1>owned</h1>" not in html
