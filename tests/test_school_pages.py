from pathlib import Path

import pytest

from alleschools.school_pages import (
    PILOT_SCHOOL_IDS,
    build_pilot_school_pages,
    build_ranked_school_pages,
    school_slug,
    select_top_schools,
)


def _school(school_id: str, name: str) -> dict:
    return {
        "id": school_id,
        "brin": school_id,
        "name": name,
        "municipality": "AMSTERDAM",
        "postcode": "1017 RV",
        "school_type": "HAVO/VWO",
        "x_linear": 94.27,
        "y_linear": 41.69,
        "size": 584,
        "years_covered": ["2020-2021", "2024-2025"],
    }


def test_school_slug_is_stable_and_readable() -> None:
    assert school_slug(_school("21AB00", "Barlaeus Gymnasium")) == "21ab00-barlaeus-gymnasium"


def test_build_pilot_pages_writes_index_details_and_discovery_files(tmp_path: Path) -> None:
    data = [_school(school_id, f"School {school_id}") for school_id in PILOT_SCHOOL_IDS]

    yearly = {
        school_id: {
            "2023-2024": {"sample": 100, "x": 92.0, "profiles": {"NT": 7.1, "NG": 6.9, "EM": 6.8, "CM": 6.7}},
            "2024-2025": {"sample": 110, "x": 94.0, "profiles": {"NT": 7.2, "NG": 7.0, "EM": 6.9, "CM": 6.8}},
        }
        for school_id in PILOT_SCHOOL_IDS
    }

    schools = build_pilot_school_pages(data, tmp_path, yearly)

    assert len(schools) == 3
    assert (tmp_path / "schools" / "index.html").exists()
    detail = tmp_path / "schools" / school_slug(data[0]) / "index.html"
    source = detail.read_text(encoding="utf-8")
    assert '<link rel="canonical"' in source
    assert 'type="application/ld+json"' in source
    assert "VWO-geslaagden / alle examenkandidaten" in source
    assert "meten niet de totale onderwijskwaliteit" in source
    assert "Ontwikkeling per schooljaar" in source
    assert 'aria-label="Trend VWO-aandeel per schooljaar"' in source
    assert "2024-2025" in source
    assert (tmp_path / "sitemap.xml").exists()
    assert "Sitemap: https://www.alleschools.nl/sitemap.xml" in (tmp_path / "robots.txt").read_text()


def test_build_pilot_pages_fails_when_governed_school_is_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ontbreken"):
        build_pilot_school_pages([], tmp_path)


def test_select_top_schools_is_descending_and_stable() -> None:
    data = [_school("00AA00", "A"), _school("00AB00", "B"), _school("00AC00", "C")]
    data[0]["x_linear"] = 80
    data[1]["x_linear"] = 90
    data[2]["x_linear"] = 90

    selected = select_top_schools(data, 2)

    assert [school["id"] for school in selected] == ["00AB00", "00AC00"]


def test_ranked_builder_generates_both_layers(tmp_path: Path) -> None:
    vo = [_school(f"V{i:05d}", f"VO {i}") | {"x_linear": 100 - i} for i in range(3)]
    po = [
        _school(f"P{i:05d}", f"PO {i}")
        | {"layer": "po", "x_linear": 90 - i, "y_linear": 400 + i}
        for i in range(3)
    ]

    result = build_ranked_school_pages(vo, po, tmp_path, limit=2)

    assert len(result["vo"]) == 2
    assert len(result["po"]) == 2
    for lang in ("nl", "en", "zh"):
        assert len(list((tmp_path / lang / "schools").glob("*/index.html"))) == 4
    assert (tmp_path / "sitemap.xml").read_text().count("<url>") == 21
    slug = school_slug(result["vo"][0])
    en_page = (tmp_path / "en" / "schools" / slug / "index.html").read_text()
    zh_page = (tmp_path / "zh" / "schools" / slug / "index.html").read_text()
    assert '<html lang="en">' in en_page
    assert "What do these figures mean?" in en_page
    assert '<html lang="zh-CN">' in zh_page
    assert "这些数字说明什么？" in zh_page
    assert 'hreflang="zh-Hans"' in en_page
    assert f"/{'zh'}/schools/{slug}/" in en_page
    assert "Website code is licensed under MIT" in en_page
    assert "网站代码采用 MIT 许可证" in zh_page
    assert "Dewei AI Advisory" in en_page
