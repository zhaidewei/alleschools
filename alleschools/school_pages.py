"""生成按公开指标筛选的可索引学校详情页。"""

from __future__ import annotations

import html
import json
import re
import shutil
import unicodedata
from pathlib import Path


PILOT_SCHOOL_IDS = ("21AB00", "15JM00", "15SC00")
TOP_SCHOOLS_PER_LAYER = 50
SITE_URL = "https://www.alleschools.nl"
PROFILE_COLORS = {"NT": "#173f35", "NG": "#c65f3b", "EM": "#4f6f8f", "CM": "#9a7b3f"}
LANGUAGES = ("nl", "en", "zh")
LANG_HTML = {"nl": "nl", "en": "en", "zh": "zh-CN"}
COPY = {
    "nl": {
        "schools": "Scholen", "method": "Data & methode", "home": "Home", "primary": "Primair onderwijs", "secondary": "Voortgezet onderwijs",
        "po_x": "VWO-equivalent schooladvies", "po_y": "Gemiddelde WOZ schoolpostcode", "po_size": "Leerlingen met advies",
        "vo_x": "VWO-geslaagden / alle examenkandidaten", "vo_y": "Bèta geslaagd", "vo_size": "Examenkandidaten in dataset",
        "core": "Kerncijfers", "meaning": "Wat zeggen deze cijfers?", "meaning_text": "De cijfers beschrijven de samenstelling en examenresultaten in openbare DUO-data over {years}. Ze meten niet de totale onderwijskwaliteit, toelatingskans of geschiktheid voor een individuele leerling.",
        "compare": "Vergelijk deze school", "compare_text": "Open de landelijke vergelijking en zoek op BRIN {brin} om deze school naast andere scholen te bekijken.", "compare_button": "Open in de schoolvergelijker",
        "source": "Bron en actualiteit", "source_text": "Bron: DUO Open Onderwijsdata{cbs}. Berekening, gebruikte jaren en beperkingen staan op de pagina {method}.", "cbs": ", aangevuld met CBS WOZ",
        "available_years": "de beschikbare schooljaren", "development": "Ontwikkeling per schooljaar", "trend_help": "De lijnen tonen de gepubliceerde waarden per schooljaar. Ontbrekende waarden blijven leeg.",
        "po_trend_x": "VWO-equivalent schooladvies (%)", "vo_trend_x": "VWO-geslaagden / alle examenkandidaten (%)", "po_trend_y": "Gemiddelde WOZ van de schoolpostcode (× €1.000)", "vo_trend_y": "Gemiddelde kernvakken per VWO-profiel",
        "trend_x_aria": "Trend VWO-aandeel per schooljaar", "po_y_aria": "Trend gemiddelde WOZ per schooljaar", "vo_y_aria": "Trend kernvakgemiddelden per profiel", "table_toggle": "Bekijk de waarden als tabel",
        "school_year": "Schooljaar", "pupils": "Leerlingen", "candidates": "Kandidaten",
        "title": "{name} in {municipality} – cijfers en vergelijking | AlleSchools", "description_po": "Bekijk openbare DUO-data voor {name} in {municipality}: VWO-equivalent advies, WOZ, omvang en gebruikte schooljaren.", "description_vo": "Bekijk openbare DUO-data voor {name} in {municipality}: VWO-aandeel, bèta-slaagpercentage, omvang en gebruikte schooljaren.",
        "index_title": "Schoolprofielen", "index_intro": "100 scholen geselecteerd op één openbaar datapunt. Dit is geen ranglijst van onderwijskwaliteit.", "index_vo": "50 VO-vestigingen met het hoogste VWO-aandeel", "index_vo_help": "Gesorteerd op VWO-geslaagden als percentage van alle examenkandidaten.", "index_po": "50 PO-scholen met het hoogste VWO-equivalente adviesaandeel", "index_po_help": "Gesorteerd op de transparante VWO-equivalente omzetting van schooladviezen.", "index_meta": "Bekijk 50 VO- en 50 PO-schoolprofielen geselecteerd op openbare DUO-indicatoren.",
        "footer": ". De websitecode valt onder de MIT-licentie. Databronnen: DUO Open Onderwijsdata (CC0 1.0) en CBS StatLine (CC BY 4.0). Dit project is niet gelieerd aan en wordt niet onderschreven door DUO of CBS.",
    },
    "en": {
        "schools": "Schools", "method": "Data & methodology", "home": "Home", "primary": "Primary education", "secondary": "Secondary education",
        "po_x": "VWO-equivalent school advice", "po_y": "Average WOZ for the school postcode", "po_size": "Pupils receiving advice",
        "vo_x": "VWO graduates / all exam candidates", "vo_y": "Science-track pass rate", "vo_size": "Exam candidates in the dataset",
        "core": "Key figures", "meaning": "What do these figures mean?", "meaning_text": "The figures describe student composition and examination results in public DUO data for {years}. They do not measure overall education quality, admission chances or suitability for an individual pupil.",
        "compare": "Compare this school", "compare_text": "Open the nationwide comparison and search for BRIN {brin} to view this school alongside others.", "compare_button": "Open in the school comparison",
        "source": "Source and recency", "source_text": "Source: DUO Open Education Data{cbs}. Calculations, years used and limitations are explained on the {method} page.", "cbs": ", supplemented with CBS WOZ data",
        "available_years": "the available school years", "development": "Development by school year", "trend_help": "The lines show published values for each school year. Missing values are left blank.",
        "po_trend_x": "VWO-equivalent school advice (%)", "vo_trend_x": "VWO graduates / all exam candidates (%)", "po_trend_y": "Average WOZ for the school postcode (× €1,000)", "vo_trend_y": "Average core-subject scores by VWO profile",
        "trend_x_aria": "VWO-share trend by school year", "po_y_aria": "Average WOZ trend by school year", "vo_y_aria": "Core-subject average trend by profile", "table_toggle": "View the values as a table",
        "school_year": "School year", "pupils": "Pupils", "candidates": "Candidates",
        "title": "{name} in {municipality} – figures and comparison | AlleSchools", "description_po": "View public DUO data for {name} in {municipality}: VWO-equivalent advice, WOZ, size and school years used.", "description_vo": "View public DUO data for {name} in {municipality}: VWO share, science-track pass rate, size and school years used.",
        "index_title": "School profiles", "index_intro": "100 schools selected using one public data point. This is not a ranking of education quality.", "index_vo": "50 secondary-school sites with the highest VWO share", "index_vo_help": "Sorted by VWO graduates as a percentage of all exam candidates.", "index_po": "50 primary schools with the highest VWO-equivalent advice share", "index_po_help": "Sorted using the transparent VWO-equivalent conversion of school advice.", "index_meta": "View 50 secondary and 50 primary school profiles selected using public DUO indicators.",
        "footer": ". Website code is licensed under MIT. Data sources: DUO Open Onderwijsdata (CC0 1.0) and CBS StatLine (CC BY 4.0). This project is not affiliated with or endorsed by DUO or CBS.",
    },
    "zh": {
        "schools": "学校", "method": "数据与方法", "home": "主页", "primary": "小学教育", "secondary": "中学教育",
        "po_x": "VWO 等值升学建议", "po_y": "学校邮编区域平均 WOZ", "po_size": "获得升学建议的学生数",
        "vo_x": "VWO 毕业生 / 全部考试学生", "vo_y": "理科方向通过率", "vo_size": "数据集中的考试学生数",
        "core": "核心数据", "meaning": "这些数字说明什么？", "meaning_text": "这些数字展示 {years} 的 DUO 公开数据中的学生构成和考试结果。它们不能衡量整体教育质量、录取机会，也不能判断学校是否适合某个学生。",
        "compare": "比较这所学校", "compare_text": "打开全荷兰学校比较工具并搜索 BRIN {brin}，即可与其他学校对比。", "compare_button": "在学校比较工具中打开",
        "source": "数据来源与时效", "source_text": "来源：DUO Open Onderwijsdata{cbs}。计算方法、所用年份和局限请参阅{method}页面。", "cbs": "，并补充 CBS WOZ 数据",
        "available_years": "现有学年", "development": "各学年变化趋势", "trend_help": "折线展示各学年的公开数值；缺失数据保留为空。",
        "po_trend_x": "VWO 等值升学建议（%）", "vo_trend_x": "VWO 毕业生 / 全部考试学生（%）", "po_trend_y": "学校邮编区域平均 WOZ（× €1,000）", "vo_trend_y": "各 VWO 方向核心科目平均分",
        "trend_x_aria": "各学年 VWO 比例趋势", "po_y_aria": "各学年平均 WOZ 趋势", "vo_y_aria": "各方向核心科目平均分趋势", "table_toggle": "以表格查看数值",
        "school_year": "学年", "pupils": "学生数", "candidates": "考试学生数",
        "title": "{name}（{municipality}）— 数据与比较 | AlleSchools", "description_po": "查看 {municipality} 的 {name} 的 DUO 公开数据，包括 VWO 等值升学建议、WOZ、规模和所用学年。", "description_vo": "查看 {municipality} 的 {name} 的 DUO 公开数据，包括 VWO 比例、理科方向通过率、规模和所用学年。",
        "index_title": "学校详情", "index_intro": "这里列出按一项公开指标筛选的 100 所学校，并非教育质量综合排名。", "index_vo": "VWO 比例最高的 50 个中学校区", "index_vo_help": "按 VWO 毕业生占全部考试学生的比例排序。", "index_po": "VWO 等值升学建议比例最高的 50 所小学", "index_po_help": "按公开透明的 VWO 等值升学建议换算结果排序。", "index_meta": "查看按 DUO 公开指标筛选的 50 所中学和 50 所小学详情。",
        "footer": "。网站代码采用 MIT 许可证。数据来源：DUO Open Onderwijsdata（CC0 1.0）与 CBS StatLine（CC BY 4.0）。本项目与 DUO、CBS 无隶属或背书关系。",
    },
}


def school_slug(school: dict) -> str:
    school = normalize_school(school)
    normalized = unicodedata.normalize("NFKD", school["name"])
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    name_part = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    return f"{school['brin'].lower()}-{name_part}"


def normalize_school(school: dict) -> dict:
    """Accepteer zowel het exportcontract als het bestaande frontendmodel."""
    return {
        "id": school.get("id") or school.get("BRIN"),
        "layer": school.get("layer") or ("po" if school.get("Y_linear", school.get("y_linear", 0)) > 100 else "vo"),
        "brin": school.get("brin") or school.get("BRIN"),
        "name": school.get("name") or school.get("naam"),
        "municipality": school.get("municipality") or school.get("gemeente"),
        "postcode": school.get("postcode") or "",
        "school_type": school.get("school_type") or school.get("type") or "",
        "x_linear": school.get("x_linear", school.get("X_linear")),
        "y_linear": school.get("y_linear", school.get("Y_linear")),
        "size": school.get("size"),
        "years_covered": school.get("years_covered") or [],
    }


def _page_shell(*, title: str, description: str, canonical: str, body: str, lang: str = "nl", alternates: dict[str, str] | None = None, schema: dict | None = None) -> str:
    copy = COPY[lang]
    schema_tag = ""
    if schema:
        schema_json = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
        schema_tag = f'<script type="application/ld+json">{schema_json}</script>'
    return f"""<!doctype html>
<html lang="{LANG_HTML[lang]}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <link rel="canonical" href="{html.escape(canonical, quote=True)}">
  {''.join(f'<link rel="alternate" hreflang="{"zh-Hans" if code == "zh" else code}" href="{html.escape(url, quote=True)}">' for code, url in (alternates or {{}}).items())}
  {f'<link rel="alternate" hreflang="x-default" href="{html.escape((alternates or {{}}).get("en", canonical), quote=True)}">' if alternates else ''}
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="AlleSchools">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:url" content="{html.escape(canonical, quote=True)}">
  <link rel="stylesheet" href="/assets/site.css">
  <script>window.va=window.va||function(){{(window.vaq=window.vaq||[]).push(arguments);}};</script>
  <script defer src="/_vercel/insights/script.js"></script>
  {schema_tag}
  <style>
    .detail-shell{{max-width:72rem;margin:0 auto;padding-left:1rem;padding-right:1rem}}
    .detail-card{{background:var(--surface);border:1px solid var(--line);border-radius:1rem;padding:1.25rem;box-shadow:0 1px 2px color-mix(in srgb,var(--ink) 5%,transparent)}}
    .metric-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.75rem}}
    .metric-value{{font:700 1.75rem/1.1 Georgia,serif;color:var(--ink)}}
    .detail-copy{{line-height:1.75;color:var(--muted)}}
    .detail-copy h2{{margin-top:2rem;margin-bottom:.5rem;font:700 1.5rem/1.2 Georgia,serif;color:var(--ink)}}
    .trend-chart{{width:100%;height:auto;overflow:visible}}
    .trend-grid{{stroke:var(--line);stroke-width:1}}
    .trend-label{{font:12px system-ui,sans-serif;fill:var(--muted)}}
    .trend-table{{width:100%;border-collapse:collapse;font-size:.875rem}}
    .trend-table th,.trend-table td{{padding:.55rem;border-bottom:1px solid var(--line);text-align:right}}
    .trend-table th:first-child,.trend-table td:first-child{{text-align:left}}
    .detail-language{{border:1px solid var(--line);border-radius:.5rem;padding:.4rem .65rem;background:var(--surface);color:var(--ink)}}
    @media (min-width:640px){{.detail-shell{{padding-left:1.5rem;padding-right:1.5rem}}}}
  </style>
</head>
<body class="min-h-screen font-sans antialiased">
  <script>document.documentElement.classList.toggle('dark',localStorage.getItem('theme')==='dark');</script>
  <header class="site-header sticky top-0 z-40 border-b backdrop-blur-md" style="border-color:var(--line);background:color-mix(in srgb,var(--page) 95%,transparent)">
    <div class="detail-shell flex min-h-[68px] items-center justify-between gap-4">
      <a href="/{lang}/" class="font-display text-2xl font-bold no-underline">Alle<span style="color:var(--accent)">Schools</span></a>
      <nav class="flex items-center gap-4 text-sm"><a class="v2-nav-link" href="/{lang}/schools/">{copy['schools']}</a><a class="v2-nav-link" href="/{lang}/methodology.html">{copy['method']}</a><select id="detailLanguage" aria-label="Language" class="detail-language"><option value="nl">NL</option><option value="en">EN</option><option value="zh">中文</option></select></nav>
    </div>
  </header>
  {body}
  <footer id="siteFooter" class="detail-shell mt-10 border-t pt-4 pb-8 text-xs leading-6" style="border-color:var(--line);color:var(--muted)">
    <p>© 2026 <a class="font-medium underline" href="https://zhaidewei.com" target="_blank" rel="noopener noreferrer">Dewei AI Advisory</a>{copy['footer']}</p>
  </footer>
  <script src="/assets/language.js"></script>
  <script>(function(){{var select=document.getElementById('detailLanguage');select.value='{lang}';select.addEventListener('change',function(){{ALLESCHOOLS_LANGUAGE.set(select.value);var next=location.pathname.replace(/^\\/(en|nl|zh)(?=\\/)/,'/'+select.value);location.assign(next+location.search+location.hash);}});}}());</script>
</body>
</html>"""


def _polyline(values: list[float | None], *, minimum: float, maximum: float) -> str:
    width, height, left, top = 720, 230, 54, 20
    plot_width, plot_height = width - left - 22, height - top - 42
    step = plot_width / max(1, len(values) - 1)
    points = []
    for index, value in enumerate(values):
        if value is None:
            continue
        x = left + index * step
        y = top + (maximum - value) / (maximum - minimum) * plot_height
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def render_trends(yearly_rows: dict, layer: str = "vo", lang: str = "nl") -> str:
    if not yearly_rows:
        return ""
    copy = COPY[lang]
    years = sorted(yearly_rows)
    x_values = [yearly_rows[year].get("x") for year in years]
    profile_values = {
        profile: [(yearly_rows[year].get("profiles") or {}).get(profile) for year in years]
        for profile in PROFILE_COLORS
    }
    x_min = max(0.0, min(float(value) for value in x_values if value is not None) - 5)
    x_max = min(100.0, max(float(value) for value in x_values if value is not None) + 5)
    if x_max <= x_min:
        x_max = x_min + 1
    secondary_values = (
        [float(yearly_rows[year]["y"]) for year in years if yearly_rows[year].get("y") is not None]
        if layer == "po"
        else [float(value) for values in profile_values.values() for value in values if value is not None]
    )
    profile_min = min(secondary_values) - (10 if layer == "po" else 0.3)
    profile_max = max(secondary_values) + (10 if layer == "po" else 0.3)

    def svg_axes(minimum: float, maximum: float) -> str:
        labels = "".join(
            f'<text class="trend-label" x="{54 + index * (644 / max(1, len(years) - 1)):.1f}" y="222" text-anchor="middle">{html.escape(year[-2:])}</text>'
            for index, year in enumerate(years)
        )
        return (
            '<line class="trend-grid" x1="54" y1="20" x2="54" y2="188"/>'
            '<line class="trend-grid" x1="54" y1="188" x2="698" y2="188"/>'
            f'<text class="trend-label" x="46" y="25" text-anchor="end">{maximum:.1f}</text>'
            f'<text class="trend-label" x="46" y="192" text-anchor="end">{minimum:.1f}</text>{labels}'
        )

    x_points = _polyline(x_values, minimum=x_min, maximum=x_max)
    x_dots = "".join(
        f'<circle cx="{54 + index * (644 / max(1, len(years) - 1)):.1f}" cy="{20 + (x_max - float(value)) / (x_max - x_min) * 168:.1f}" r="4" fill="#c65f3b"><title>{html.escape(year)}: {float(value):.2f}%</title></circle>'
        for index, (year, value) in enumerate(zip(years, x_values)) if value is not None
    )
    profile_lines = "".join(
        f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{_polyline(profile_values[profile], minimum=profile_min, maximum=profile_max)}"/>'
        for profile, color in PROFILE_COLORS.items()
    )
    legend = " ".join(
        f'<span class="inline-flex items-center gap-1"><i style="display:inline-block;width:.8rem;height:.18rem;background:{color}"></i>{profile}</span>'
        for profile, color in PROFILE_COLORS.items()
    )
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(year)}</td><td>{yearly_rows[year].get('sample', '—')}</td>"
        f"<td>{yearly_rows[year].get('x', '—')}</td>"
        + "".join(f"<td>{(yearly_rows[year].get('profiles') or {}).get(profile, '—')}</td>" for profile in PROFILE_COLORS)
        + "</tr>"
        for year in years
    )
    if layer == "po":
        y_values = [yearly_rows[year].get("y") for year in years]
        secondary_chart = f'''<section class="detail-card mt-4">
        <h3 class="font-bold">{copy['po_trend_y']}</h3>
        <svg class="trend-chart mt-3" viewBox="0 0 720 230" role="img" aria-label="{copy['po_y_aria']}">{svg_axes(profile_min, profile_max)}<polyline fill="none" stroke="#173f35" stroke-width="3" points="{_polyline(y_values, minimum=profile_min, maximum=profile_max)}"/></svg>
      </section>'''
        rows = "".join(
            f"<tr><td>{html.escape(year)}</td><td>{yearly_rows[year].get('sample', '—')}</td><td>{yearly_rows[year].get('x', '—')}</td><td>{yearly_rows[year].get('y', '—')}</td></tr>"
            for year in years
        )
        table_head = f"<th>{copy['school_year']}</th><th>{copy['pupils']}</th><th>VWO-equivalent %</th><th>WOZ × €1.000</th>"
    else:
        secondary_chart = f'''<section class="detail-card mt-4">
        <h3 class="font-bold">{copy['vo_trend_y']}</h3>
        <p class="mt-2 flex flex-wrap gap-4 text-sm">{legend}</p>
        <svg class="trend-chart mt-3" viewBox="0 0 720 230" role="img" aria-label="{copy['vo_y_aria']}">{svg_axes(profile_min, profile_max)}{profile_lines}</svg>
      </section>'''
        table_head = f"<th>{copy['school_year']}</th><th>{copy['candidates']}</th><th>VWO %</th><th>NT</th><th>NG</th><th>EM</th><th>CM</th>"
    primary_heading = copy["po_trend_x"] if layer == "po" else copy["vo_trend_x"]
    return f"""
      <h2>{copy['development']}</h2>
      <p>{copy['trend_help']}</p>
      <section class="detail-card mt-4">
        <h3 class="font-bold">{primary_heading}</h3>
        <svg class="trend-chart mt-3" viewBox="0 0 720 230" role="img" aria-label="{copy['trend_x_aria']}">{svg_axes(x_min, x_max)}<polyline fill="none" stroke="#c65f3b" stroke-width="3" points="{x_points}"/>{x_dots}</svg>
      </section>
      {secondary_chart}
      <details class="mt-4"><summary class="cursor-pointer font-semibold">{copy['table_toggle']}</summary>
        <div class="mt-2 overflow-x-auto"><table class="trend-table"><thead><tr>{table_head}</tr></thead><tbody>{rows}</tbody></table></div>
      </details>"""


def render_school_page(school: dict, yearly_rows: dict | None = None, lang: str = "nl") -> str:
    school = normalize_school(school)
    copy = COPY[lang]
    name = str(school["name"])
    municipality = str(school["municipality"]).title()
    slug = school_slug(school)
    layer = school["layer"]
    canonical = f"{SITE_URL}/{lang}/schools/{slug}/"
    alternates = {code: f"{SITE_URL}/{code}/schools/{slug}/" for code in LANGUAGES}
    years = school.get("years_covered") or []
    year_text = f"{years[0]}–{years[-1]}" if years else copy["available_years"]
    description = copy["description_po" if layer == "po" else "description_vo"].format(name=name, municipality=municipality)
    schema = {
        "@context": "https://schema.org",
        "@type": "School",
        "name": name,
        "identifier": school["brin"],
        "address": {
            "@type": "PostalAddress",
            "postalCode": school.get("postcode", ""),
            "addressLocality": municipality,
            "addressCountry": "NL",
        },
        "url": canonical,
    }
    level_label = copy["primary"] if layer == "po" else copy["secondary"]
    metric_cards = (
        f'''<article class="detail-card"><p class="text-sm" style="color:var(--muted)">{copy['po_x']}</p><p class="metric-value mt-2">{school['x_linear']:.2f}%</p></article>
      <article class="detail-card"><p class="text-sm" style="color:var(--muted)">{copy['po_y']}</p><p class="metric-value mt-2">€ {school['y_linear']:.0f}k</p></article>
      <article class="detail-card"><p class="text-sm" style="color:var(--muted)">{copy['po_size']}</p><p class="metric-value mt-2">{int(school['size'])}</p></article>'''
        if layer == "po"
        else f'''<article class="detail-card"><p class="text-sm" style="color:var(--muted)">{copy['vo_x']}</p><p class="metric-value mt-2">{school['x_linear']:.2f}%</p></article>
      <article class="detail-card"><p class="text-sm" style="color:var(--muted)">{copy['vo_y']}</p><p class="metric-value mt-2">{school['y_linear']:.2f}%</p></article>
      <article class="detail-card"><p class="text-sm" style="color:var(--muted)">{copy['vo_size']}</p><p class="metric-value mt-2">{int(school['size'])}</p></article>'''
    )
    body = f"""
  <main class="detail-shell py-10 sm:py-14">
    <nav class="mb-6 text-sm" aria-label="Breadcrumb"><a href="/{lang}/">{copy['home']}</a> / <a href="/{lang}/schools/">{copy['schools']}</a> / {html.escape(name)}</nav>
    <p class="text-sm font-bold uppercase tracking-widest" style="color:var(--accent)">{level_label} · {html.escape(municipality)}</p>
    <h1 class="mt-2 font-display text-4xl font-bold tracking-tight sm:text-5xl">{html.escape(name)}</h1>
    <p class="mt-3 text-lg" style="color:var(--muted)">{html.escape(school['school_type'])} · BRIN {html.escape(school['brin'])} · {html.escape(school.get('postcode', ''))}</p>

    <section class="metric-grid mt-8" aria-label="{copy['core']}">
      {metric_cards}
    </section>

    <div class="detail-copy">
      <h2>{copy['meaning']}</h2>
      <p>{copy['meaning_text'].format(years=html.escape(year_text))}</p>
      {render_trends(yearly_rows or {}, layer, lang)}
      <h2>{copy['compare']}</h2>
      <p>{copy['compare_text'].format(brin=f'<strong>{html.escape(school["brin"])}</strong>')}</p>
      <p class="mt-5"><a class="inline-flex rounded-lg px-4 py-3 font-semibold text-white no-underline" style="background:var(--accent)" href="/{lang}/?mode={layer}&amp;q={html.escape(school['brin'], quote=True)}">{copy['compare_button']}</a></p>
      <h2>{copy['source']}</h2>
      <p>{copy['source_text'].format(cbs=copy['cbs'] if layer == 'po' else '', method=f'<a href="/{lang}/methodology.html">{copy["method"]}</a>')}</p>
    </div>
  </main>"""
    return _page_shell(
        title=copy["title"].format(name=name, municipality=municipality),
        description=description,
        canonical=canonical,
        body=body,
        lang=lang,
        alternates=alternates,
        schema=schema,
    )


def select_top_schools(data: list[dict], limit: int = TOP_SCHOOLS_PER_LAYER) -> list[dict]:
    schools = [normalize_school(school) for school in data]
    eligible = [school for school in schools if school["x_linear"] is not None]
    return sorted(eligible, key=lambda school: (-float(school["x_linear"]), school["id"]))[:limit]


def render_school_index(vo_schools: list[dict], po_schools: list[dict], lang: str = "nl") -> str:
    copy = COPY[lang]
    def cards(schools: list[dict]) -> str:
        return "".join(
            f'<li class="detail-card"><a class="text-lg font-bold" href="/{lang}/schools/{school_slug(s)}/">{html.escape(s["name"])}</a>'
            f'<p class="mt-1 text-sm" style="color:var(--muted)">{html.escape(str(s["municipality"]).title())} · BRIN {html.escape(s["brin"])} · {s["x_linear"]:.2f}%</p></li>'
            for s in schools
        )
    body = f"""<main class="detail-shell py-10 sm:py-14">
      <h1 class="mt-2 font-display text-4xl font-bold">{copy['index_title']}</h1>
      <p class="mt-3 detail-copy">{copy['index_intro']}</p>
      <h2 class="mt-10 font-display text-2xl font-bold">{copy['index_vo']}</h2>
      <p class="mt-2 detail-copy">{copy['index_vo_help']}</p>
      <ol class="mt-5 grid gap-3">{cards(vo_schools)}</ol>
      <h2 class="mt-12 font-display text-2xl font-bold">{copy['index_po']}</h2>
      <p class="mt-2 detail-copy">{copy['index_po_help']}</p>
      <ol class="mt-5 grid gap-3">{cards(po_schools)}</ol>
    </main>"""
    return _page_shell(
        title=f"{copy['index_title']} | AlleSchools",
        description=copy["index_meta"],
        canonical=f"{SITE_URL}/{lang}/schools/",
        body=body,
        lang=lang,
        alternates={code: f"{SITE_URL}/{code}/schools/" for code in LANGUAGES},
    )


def build_pilot_school_pages(
    data_vo: list[dict], public_dir: str | Path, yearly_vo: dict | None = None
) -> list[dict]:
    normalized = [normalize_school(school) for school in data_vo]
    by_id = {school["id"]: school for school in normalized}
    missing = [school_id for school_id in PILOT_SCHOOL_IDS if school_id not in by_id]
    if missing:
        raise ValueError(f"Pilot school IDs ontbreken in VO-data: {', '.join(missing)}")

    schools = [by_id[school_id] for school_id in PILOT_SCHOOL_IDS]
    root = Path(public_dir)
    schools_root = root / "schools"
    schools_root.mkdir(parents=True, exist_ok=True)
    (schools_root / "index.html").write_text(render_school_index(schools, []), encoding="utf-8")
    for school in schools:
        page_dir = schools_root / school_slug(school)
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(
            render_school_page(school, (yearly_vo or {}).get(school["id"], {})), encoding="utf-8"
        )

    urls = [f"{SITE_URL}/schools/"] + [f"{SITE_URL}/schools/{school_slug(s)}/" for s in schools]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(f"  <url><loc>{html.escape(url)}</loc></url>" for url in [f"{SITE_URL}/", f"{SITE_URL}/methodology.html", *urls])
    sitemap += "\n</urlset>\n"
    (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (root / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    return schools


def build_ranked_school_pages(
    data_vo: list[dict],
    data_po: list[dict],
    public_dir: str | Path,
    yearly_comparison: dict | None = None,
    limit: int = TOP_SCHOOLS_PER_LAYER,
) -> dict[str, list[dict]]:
    vo_schools = select_top_schools([{**school, "layer": "vo"} for school in data_vo], limit)
    po_schools = select_top_schools([{**school, "layer": "po"} for school in data_po], limit)
    schools = vo_schools + po_schools
    root = Path(public_dir)
    yearly = yearly_comparison or {}
    legacy_root = root / "schools"
    if legacy_root.exists():
        shutil.rmtree(legacy_root)
    urls = []
    for lang in LANGUAGES:
        schools_root = root / lang / "schools"
        if schools_root.exists():
            shutil.rmtree(schools_root)
        schools_root.mkdir(parents=True, exist_ok=True)
        (schools_root / "index.html").write_text(
            render_school_index(vo_schools, po_schools, lang), encoding="utf-8"
        )
        urls.append(f"{SITE_URL}/{lang}/schools/")
        for school in schools:
            page_dir = schools_root / school_slug(school)
            page_dir.mkdir(parents=True, exist_ok=True)
            rows = (yearly.get(school["layer"]) or {}).get(school["id"], {})
            (page_dir / "index.html").write_text(
                render_school_page(school, rows, lang), encoding="utf-8"
            )
            urls.append(f"{SITE_URL}/{lang}/schools/{school_slug(school)}/")
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(
        f"  <url><loc>{html.escape(url)}</loc></url>"
        for url in [
            *[f"{SITE_URL}/{lang}/" for lang in ("en", "nl", "zh")],
            *[f"{SITE_URL}/{lang}/methodology.html" for lang in ("en", "nl", "zh")],
            *urls,
        ]
    )
    sitemap += "\n</urlset>\n"
    (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (root / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )
    return {"vo": vo_schools, "po": po_schools}
