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
    assert "学校升学建议与周边房价经常同向变化" in methodology
    assert 'id="insightTitle"' not in home
    assert 'id="insightBody"' not in home


def test_explorer_flow_is_visually_ordered() -> None:
    home = (PROJECT_ROOT / "view_xy.html").read_text(encoding="utf-8")
    css = (PROJECT_ROOT / "assets" / "tailwind-input.css").read_text(encoding="utf-8")
    assert '"mode chart" "school-search chart" "filters chart"' in css
    assert 'class="flow-arrow ' not in home
    assert "学校探索器" not in home
    assert "🏫" not in home
    assert "选择小学或中学" in home
    assert "搜索学校" in home
    assert "筛选范围" in home
    assert 'class="site-header sticky top-0 z-40' in home
    assert 'class="hero-panel ' in home
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr))' in css
    assert '#mainChartWrap { height: min(68vh, 35rem); min-height: 27rem; aspect-ratio: auto; }' in css
    assert "function applyResponsiveChartSizing()" in home
    assert "var tickSize = mobile ? 9 : 12" in home
    assert "var titleSize = mobile ? 10 : 12" in home
    assert "function applyResponsiveComparisonSizing()" in home
    assert "boxWidth: mobile ? 14 : 40" in home
    assert "function updateProfileTabsVisibility()" in home
    assert "profileTabs.style.display = hiddenForPrimary ? 'none' : ''" in home


def test_primary_navigation_is_consistent_on_both_pages() -> None:
    home = (PROJECT_ROOT / "view_xy.html").read_text(encoding="utf-8")
    methodology = (PROJECT_ROOT / "methodology.html").read_text(encoding="utf-8")

    for source in (home, methodology):
        assert 'id="navHome"' in source
        assert 'id="navMethodology"' in source
        assert 'id="navSupport"' in source
        assert 'href="https://ko-fi.com/deweizhai"' in source
        assert 'id="navContact"' not in source

    assert 'id="supportSection"' not in home
    assert 'id="contactSection"' not in home
    assert 'id="contactTitle"' not in home


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
    assert "网站代码采用 MIT 许可证" in home
    assert "DUO Open Onderwijsdata（CC0 1.0）" in home
    assert "CBS StatLine（CC BY 4.0）" in home
