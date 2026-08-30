from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_visible_copy_avoids_uncontracted_ranking_language() -> None:
    sources = [
        PROJECT_ROOT / "view_xy.html",
        PROJECT_ROOT / "methodology.html",
        PROJECT_ROOT / "demo" / "demo_po_meta.json",
        PROJECT_ROOT / "demo" / "demo_vo_meta.json",
    ]
    prohibited = (
        "best",
        "elite",
        "strength",
        "most academic",
        "最佳",
        "精英",
        "更强",
        "学术性最强",
        "sterker",
        "beste",
        "meest academisch",
    )

    for source in sources:
        text = source.read_text(encoding="utf-8").casefold()
        for term in prohibited:
            assert term.casefold() not in text, f"{source.name} contains ranking language: {term}"


def test_methodology_is_a_dedicated_page() -> None:
    home = (PROJECT_ROOT / "view_xy.html").read_text(encoding="utf-8")
    methodology = (PROJECT_ROOT / "methodology.html").read_text(encoding="utf-8")
    assert 'href="methodology.html?lang=en"' in home
    assert 'id="algorithmSection"' not in home
    assert 'id="navData"' not in home
    assert 'id="disclaimerSection"' not in home
    assert 'data-lang="zh"' in methodology
    assert 'data-lang="en"' in methodology
    assert 'data-lang="nl"' in methodology
    assert 'id="vo"' in methodology
    assert 'id="po"' in methodology


def test_province_filter_is_available_in_all_languages() -> None:
    home = (PROJECT_ROOT / "view_xy.html").read_text(encoding="utf-8")
    assert 'id="provinceFilter"' in home
    assert "labelProvince: 'Province'" in home
    assert "labelProvince: '省份'" in home
    assert "labelProvince: 'Provincie'" in home
    assert "allProvinces: 'All provinces'" in home
    assert "allProvinces: '全部省份'" in home
    assert "allProvinces: 'Alle provincies'" in home


def test_filter_flow_has_one_text_search_entry() -> None:
    home = (PROJECT_ROOT / "view_xy.html").read_text(encoding="utf-8")
    assert home.count('id="schoolSearch"') == 1
    assert 'id="gemeenteFilter"' not in home
    assert 'id="mobileSchoolSearch"' not in home
    assert 'id="cityFilterTrigger"' in home
    assert 'id="schoolFilterTrigger"' in home
    assert 'id="cityFilterMenu"' in home
    assert 'id="schoolFilterMenu"' in home
    assert 'class="school-search-panel ' in home
    assert 'id="gemeenteList"' not in home
    assert 'id="mobileFiltersSheet"' not in home


def test_footer_links_to_advisory_homepage() -> None:
    home = (PROJECT_ROOT / "view_xy.html").read_text(encoding="utf-8")
    assert 'href="https://zhaidewei.com"' in home
    assert '>Dewei AI Advisory</a>' in home
    assert "copyrightLicense: '。本项目采用 MIT 许可证。'" in home
