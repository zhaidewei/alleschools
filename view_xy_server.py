#!/usr/bin/env python3
"""
读取 schools_xy_coords.csv，生成带散点图的 HTML，并在本地启动 HTTP 服务。
浏览器打开后显示：横轴 VWO 通过人数占比，纵轴 理科占比；可切换线性/对数坐标。
"""
import argparse
import csv
import json
import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "schools_xy_coords.csv")
EXCLUDED_PATH = os.path.join(BASE, "excluded_schools.json")
HTML_PATH = os.path.join(BASE, "view_xy.html")
PUBLIC_INDEX = os.path.join(BASE, "public", "index.html")
PORT = 8082


def load_excluded():
    if not os.path.exists(EXCLUDED_PATH):
        return []
    try:
        with open(EXCLUDED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def load_data():
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            # 人数：优先用 candidates_total（5 年考生总数），兼容旧 CSV 的 HAVO_geslaagd_total
            size_raw = r.get("candidates_total") or r.get("HAVO_geslaagd_total") or 0
            try:
                size = int(size_raw)
            except (ValueError, TypeError):
                size = 0
            rows.append({
                "BRIN": r["BRIN"],
                "naam": r["vestigingsnaam"],
                "gemeente": r["gemeente"],
                "type": r["type"],
                "X_linear": float(r["X_linear"]),
                "Y_linear": float(r["Y_linear"]),
                "X_log": float(r["X_log"]),
                "Y_log": float(r["Y_log"]),
                "size": size,
            })
    return rows


def build_html(data, excluded=None):
    excluded = excluded if excluded is not None else []
    data_js = json.dumps(data, ensure_ascii=False)
    excluded_js = json.dumps(excluded, ensure_ascii=False)
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dutch secondary school map (excluding international schools): academic level × science focus</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    tailwind.config = { darkMode: 'class', theme: { extend: { fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] } } } }
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <script>document.documentElement.classList.toggle('dark', localStorage.getItem('theme')==='dark');</script>
</head>
<body class="min-h-screen bg-slate-50 text-slate-800 dark:bg-slate-900 dark:text-slate-200 font-sans antialiased">
  <div id="wrap" class="max-w-6xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex justify-end items-center gap-4 mb-2">
      <div class="flex items-center gap-2">
        <span id="labelTheme" class="text-sm font-medium text-slate-600 dark:text-slate-400">Theme</span>
        <button type="button" id="themeLight" class="px-2.5 py-1 text-sm rounded-md border border-slate-300 dark:border-slate-500 text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 focus:outline-none focus:ring-1 focus:ring-slate-400">Light</button>
        <button type="button" id="themeDark" class="px-2.5 py-1 text-sm rounded-md border border-slate-300 dark:border-slate-500 text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 focus:outline-none focus:ring-1 focus:ring-slate-400">Dark</button>
      </div>
      <div class="flex items-center gap-2">
        <label id="labelLanguage" class="text-sm font-medium text-slate-600 dark:text-slate-400">Language</label>
        <select id="langSelect" class="rounded-lg border border-slate-300 dark:border-slate-500 px-3 py-1.5 text-sm text-slate-800 dark:text-slate-200 dark:bg-slate-700 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 align-middle">
          <option value="en">English</option>
          <option value="zh">中文</option>
          <option value="nl">Nederlands</option>
        </select>
      </div>
    </div>
    <div id="chartWrap" class="mb-8">
      <h1 id="titleMain" class="text-xl font-semibold text-slate-800 dark:text-slate-100 tracking-tight"><a href="/" class="text-slate-800 dark:text-slate-100 hover:text-slate-600 dark:hover:text-slate-300">Dutch secondary school map (excluding international schools)</a>: academic level × science focus</h1>
      <p id="subtitleMain" class="mt-1 text-sm text-slate-500 dark:text-slate-400">Data from DUO. X = academic strength, Y = science share. Dot size = graduation count. <strong id="schoolCount" class="font-medium text-slate-700 dark:text-slate-300">0</strong> schools shown.</p>
      <div class="mt-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200/80 dark:border-slate-600 shadow-sm p-4 sm:p-6">
        <div class="w-full aspect-[4/3] min-h-[420px]">
          <canvas id="chart" class="w-full h-full block"></canvas>
        </div>
      </div>
    </div>
    <div class="controls flex flex-wrap items-center gap-4 sm:gap-6 py-4 px-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200/80 dark:border-slate-600 shadow-sm">
      <div class="flex items-center gap-2">
        <label id="labelSchoolSearch" class="text-sm font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">School search</label>
        <input type="text" id="schoolSearch" placeholder="Search by name or BRIN, matches highlighted" class="flex-1 min-w-[200px] rounded-lg border border-slate-300 dark:border-slate-500 px-3 py-2 text-sm text-slate-800 dark:text-slate-200 dark:bg-slate-700 placeholder-slate-400 dark:placeholder-slate-500 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400">
      </div>
      <div class="flex items-center gap-2">
        <label id="labelGemeente" class="text-sm font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">City hall filter</label>
        <input type="text" id="gemeenteFilter" placeholder="Leave empty for all, comma for multiple" class="flex-1 min-w-[180px] rounded-lg border border-slate-300 dark:border-slate-500 px-3 py-2 text-sm text-slate-800 dark:text-slate-200 dark:bg-slate-700 placeholder-slate-400 dark:placeholder-slate-500 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400">
      </div>
      <div class="flex flex-wrap items-center gap-4">
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm text-slate-600 dark:text-slate-400">
          <input type="radio" name="coord" value="linear" checked class="rounded-full border-slate-300 text-slate-600 focus:ring-slate-400">
          <span id="labelLinear">Linear scale</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm text-slate-600 dark:text-slate-400">
          <input type="radio" name="coord" value="log" class="rounded-full border-slate-300 text-slate-600 focus:ring-slate-400">
          <span id="labelLog">Log scale</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm text-slate-600 dark:text-slate-400">
          <input type="checkbox" id="showVMBO" class="rounded border-slate-300 text-slate-600 focus:ring-slate-400">
          <span id="labelShowVMBO">Show VMBO-only schools</span>
        </label>
      </div>
    </div>
    <div id="gemeenteList" class="mt-8 pt-6 border-t border-slate-200 dark:border-slate-600">
      <div class="gemeente-list-header flex flex-wrap items-center gap-4 mb-3">
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm font-medium text-slate-600 dark:text-slate-400">
          <input type="checkbox" id="selectAll" class="rounded border-slate-300 text-slate-600 focus:ring-slate-400">
          <span id="labelSelectAll">Select all</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm font-medium text-slate-600 dark:text-slate-400">
          <input type="checkbox" id="deselectAll" class="rounded border-slate-300 text-slate-600 focus:ring-slate-400">
          <span id="labelDeselectAll">Deselect all</span>
        </label>
      </div>
      <div id="gemeenteCheckboxes" class="max-h-56 overflow-y-auto flex flex-wrap gap-x-4 gap-y-2"></div>
    </div>
    <div id="excludedSection" class="mt-8 pt-6 border-t border-slate-200 dark:border-slate-600 text-sm text-slate-500 dark:text-slate-400"></div>
    <div id="algorithmSection" class="mt-8 pt-6 border-t border-slate-200 dark:border-slate-600 text-sm text-slate-600 dark:text-slate-400">
      <h2 id="algorithmTitle" class="text-base font-semibold text-slate-700 dark:text-slate-300 mb-3"></h2>
      <div id="algorithmBody" class="space-y-2 prose prose-slate max-w-none text-sm"></div>
    </div>
    <div id="disclaimerSection" class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-600 text-sm text-slate-500 dark:text-slate-400">
      <h2 id="disclaimerTitle" class="text-base font-semibold text-slate-700 dark:text-slate-300 mb-2"></h2>
      <p id="disclaimerBody" class="text-slate-500 dark:text-slate-400"></p>
    </div>
    <div id="contactSection" class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-600 text-sm text-slate-500 dark:text-slate-400 pb-4">
      <h2 id="contactTitle" class="text-base font-semibold text-slate-700 dark:text-slate-300 mb-2"></h2>
      <p class="text-slate-600 dark:text-slate-400">
        <a href="mailto:dewei.zhai@gmail.com" class="text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 underline">dewei.zhai@gmail.com</a>
        &nbsp;·&nbsp;
        <a href="https://www.linkedin.com/in/zhaidewei/" target="_blank" rel="noopener noreferrer" class="text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 underline">LinkedIn</a>
      </p>
    </div>
    <div id="supportSection" class="mt-4 pt-4 border-t border-slate-200 dark:border-slate-600 text-sm pb-4">
      <p class="text-slate-600 dark:text-slate-400 mb-2">
        <a id="supportLink" href="https://ko-fi.com/deweizhai" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg bg-amber-500/90 hover:bg-amber-500 px-4 py-2 text-sm font-medium text-white no-underline shadow-sm">Ko-fi</a>
      </p>
      <p id="supportHint" class="text-slate-500 dark:text-slate-400 text-xs"></p>
    </div>
    <footer id="copyrightSection" class="mt-4 pt-4 border-t border-slate-200 dark:border-slate-600 text-xs text-slate-400 dark:text-slate-500 pb-8">
      <p id="copyrightText"></p>
    </footer>
  </div>
  <script>
    (function() {
      const excluded = """ + excluded_js + """;
      const el = document.getElementById('excludedSection');
      if (excluded.length === 0) { el.innerHTML = ''; return; }
      el.innerHTML = '<h2 id="excludedTitle" class="text-base font-semibold text-slate-700 dark:text-slate-300 mb-2"></h2><p id="excludedDesc" class="mb-3 text-slate-500 dark:text-slate-400"></p><ul class="list-disc pl-5 max-h-44 overflow-y-auto space-y-1 text-slate-600 dark:text-slate-400">' +
        excluded.map(function(s) { return '<li>' + (s.BRIN || '') + ' ' + (s.naam || '') + ' (' + (s.gemeente || '') + ')</li>'; }).join('') + '</ul>';
    })();
  </script>
  <script>
    const data = """ + data_js + """;
    let currentLang = localStorage.getItem('schools-lang') || 'en';
    const L = {
      en: {
        labelLanguage: 'Language',
        labelTheme: 'Theme',
        labelLight: 'Light',
        labelDark: 'Dark',
        titleMain: 'Dutch secondary school map (excluding international schools): academic level × science focus',
        subtitleBefore: 'Data from DUO. X = academic strength, Y = science share. Dot size = graduation count. ',
        subtitleAfter: ' schools shown.',
        labelSchoolSearch: 'School search',
        schoolSearchPlaceholder: 'Search by name or BRIN, matches highlighted',
        labelGemeente: 'City hall filter',
        gemeentePlaceholder: 'Leave empty for all, comma for multiple',
        labelLinear: 'Linear scale',
        labelLog: 'Log scale',
        labelShowVMBO: 'Show VMBO-only schools',
        labelSelectAll: 'Select all',
        labelDeselectAll: 'Deselect all',
        excludedTitle: 'Schools excluded (too few data points)',
        excludedDesc: 'The following schools were not included in the chart because HAVO/VWO exam candidates (5-year total) are below 20.',
        axisXLinear: 'VWO share (%) — 100% most academic',
        axisXLog: 'VWO share (log10(1+x/100))',
        axisYLinear: 'Science share (%)',
        axisYLog: 'Science share (log10(1+y/100))',
        tooltipCandidates: '5-yr candidates',
        algorithmTitle: 'How X and Y are calculated',
        algorithmBody: '<p><strong>X (horizontal):</strong> VWO share = VWO passed / total exam candidates (all tracks: HAVO, VWO, VMBO) at the school, as a percentage (0–100%). Higher X means more academically oriented (more VWO).</p><p><strong>Y (vertical):</strong> Science share = science passed / total exam candidates. For HAVO/VWO schools, science = the following profiles (bèta):</p><ul class="list-disc pl-5 my-1"><li><strong>N&amp;T</strong> — Natuur &amp; Techniek (Nature &amp; Technology): maths, physics, chemistry, technical subjects.</li><li><strong>N&amp;G</strong> — Natuur &amp; Gezondheid (Nature &amp; Health): biology, chemistry, health-related subjects.</li><li><strong>N&amp;T/N&amp;G</strong> — combination profile of N&amp;T and N&amp;G.</li></ul><p>For VMBO-only schools, Y = techniek share within VMBO, and X is set to 0.</p><p>Both X and Y are <strong>weighted averages</strong> over school years 2019–2020 to 2023–2024, with recent years weighted more. Dot size = graduation count (5-year sum) at the school.</p>',
        disclaimerTitle: 'Disclaimer',
        disclaimerBody: 'Data from DUO Open Onderwijsdata (exam candidates and pass counts). This tool is for reference only; no warranty of accuracy or fitness for any decision. Not affiliated with DUO or the Dutch government.',
        contactTitle: 'Contact',
        supportHint: 'Like this tool? Buy me a coffee on Ko-fi.',
        copyrightText: '© 2025 Dewei Zhai. This project is licensed under the MIT License.'
      },
      zh: {
        labelLanguage: '语言',
        labelTheme: '主题',
        labelLight: '浅色',
        labelDark: '深色',
        titleMain: '荷兰中学定位图(不含国际学校)：学术度 × 理科度',
        subtitleBefore: '数据来自DUO，X轴代表学术强度，Y轴代表理科占比，点的大小代表毕业人数。共 ',
        subtitleAfter: ' 所学校。',
        labelSchoolSearch: '学校搜索',
        schoolSearchPlaceholder: '按校名或 BRIN 搜索，匹配项高亮',
        labelGemeente: '市政厅 过滤',
        gemeentePlaceholder: '不输入显示全部，多个用逗号分隔',
        labelLinear: '线性坐标',
        labelLog: '对数坐标',
        labelShowVMBO: '显示纯 VMBO 学校',
        labelSelectAll: '全选',
        labelDeselectAll: '全部取消',
        excludedTitle: '因数据点过少未纳入图表的学校',
        excludedDesc: '以下学校因 HAVO/VWO 考生数过少（5 年合计 < 20）未参与坐标计算，故未出现在上图中。',
        axisXLinear: 'VWO 通过人数占比 (%) — 100% 学术性最强',
        axisXLog: 'VWO 通过人数占比 (log10(1+x/100))',
        axisYLinear: '理科占比 (%)',
        axisYLog: '理科占比 (log10(1+y/100))',
        tooltipCandidates: '5年考生',
        algorithmTitle: 'X 与 Y 的计算方式',
        algorithmBody: '<p><strong>X（横轴）：</strong>VWO 通过人数占比 = 该校 VWO 通过人数 / 该校全部考生总数（HAVO、VWO、VMBO 等），以百分比表示（0–100%）。X 越高表示越偏学术（VWO 越多）。</p><p><strong>Y（纵轴）：</strong>理科通过人数占比 = 理科通过人数 / 该校全部考生总数。HAVO/VWO 学校的理科指以下方向（bèta）：</p><ul class="list-disc pl-5 my-1"><li><strong>N&amp;T</strong> — Natuur &amp; Techniek（自然与技术）：数学、物理、化学、技术等。</li><li><strong>N&amp;G</strong> — Natuur &amp; Gezondheid（自然与健康）：生物、化学、健康相关等。</li><li><strong>N&amp;T/N&amp;G</strong> — N&amp;T 与 N&amp;G 的组合方向。</li></ul><p>仅 VMBO 的学校 Y 为 VMBO 内 techniek 占比，X 固定为 0。</p><p>X、Y 均为 2019–2020 至 2023–2024 学年的<strong>加权平均</strong>，近年权重更大。圆点大小表示该校 5 年毕业人数。</p>',
        disclaimerTitle: '免责声明',
        disclaimerBody: '数据来自 DUO Open Onderwijsdata（考试考生与通过人数）。本工具仅供参考，不保证准确或适用于任何决策；与 DUO 及荷兰政府无关联。',
        contactTitle: '联系作者',
        supportHint: '觉得有用？请在 Ko-fi 请我喝杯咖啡。',
        copyrightText: '© 2025 翟德炜。本项目采用 MIT 许可证。'
      },
      nl: {
        labelLanguage: 'Taal',
        labelTheme: 'Thema',
        labelLight: 'Licht',
        labelDark: 'Donker',
        titleMain: 'Nederlandse schoolkaart voortgezet onderwijs (zonder internationale scholen): academisch × bèta',
        subtitleBefore: 'Data van DUO. X = academisch niveau, Y = bètandeel. Puntgrootte = aantal geslaagden. ',
        subtitleAfter: ' scholen getoond.',
        labelSchoolSearch: 'Zoek school',
        schoolSearchPlaceholder: 'Zoek op naam of BRIN, treffers gemarkeerd',
        labelGemeente: 'Gemeentefilter',
        gemeentePlaceholder: 'Leeg = alle, komma voor meerdere',
        labelLinear: 'Lineaire schaal',
        labelLog: 'Logschaal',
        labelShowVMBO: 'Toon alleen VMBO-scholen',
        labelSelectAll: 'Alles selecteren',
        labelDeselectAll: 'Alles deselecteren',
        excludedTitle: 'Scholen uitgesloten (te weinig datapunten)',
        excludedDesc: 'De volgende scholen zijn niet in de grafiek opgenomen omdat HAVO/VWO-examenkandidaten (5-jaar totaal) onder 20 liggen.',
        axisXLinear: 'VWO-aandeel (%) — 100% meest academisch',
        axisXLog: 'VWO-aandeel (log10(1+x/100))',
        axisYLinear: 'Bètandeel (%)',
        axisYLog: 'Bètandeel (log10(1+y/100))',
        tooltipCandidates: '5-jaar kandidaten',
        algorithmTitle: 'Hoe X en Y worden berekend',
        algorithmBody: '<p><strong>X (horizontaal):</strong> VWO-aandeel = VWO geslaagden / totaal examenkandidaten (alle richtingen: HAVO, VWO, VMBO) van de school, in procent (0–100%). Hogere X = meer academisch (meer VWO).</p><p><strong>Y (verticaal):</strong> Bètandeel = bètageslaagden / totaal examenkandidaten. Voor HAVO/VWO-scholen is bèta de volgende profielen:</p><ul class="list-disc pl-5 my-1"><li><strong>N&amp;T</strong> — Natuur &amp; Techniek: wiskunde, natuurkunde, scheikunde, technische vakken.</li><li><strong>N&amp;G</strong> — Natuur &amp; Gezondheid: biologie, scheikunde, gezondheidsgerelateerde vakken.</li><li><strong>N&amp;T/N&amp;G</strong> — combinatieprofiel van N&amp;T en N&amp;G.</li></ul><p>Voor alleen VMBO-scholen is Y het techniekaandeel binnen VMBO en X = 0.</p><p>X en Y zijn <strong>gewogen gemiddelden</strong> over schooljaren 2019–2020 t/m 2023–2024, met zwaardere weging voor recente jaren. Puntgrootte = aantal geslaagden (5-jaar som) van de school.</p>',
        disclaimerTitle: 'Disclaimer',
        disclaimerBody: 'Data van DUO Open Onderwijsdata (examenkandidaten en geslaagden). Dit hulpmiddel is alleen voor referentie; geen garantie op juistheid of geschiktheid voor beslissingen. Niet gelieerd aan DUO of de overheid.',
        contactTitle: 'Contact',
        supportHint: 'Waardevol? Trakteer me op een koffie via Ko-fi.',
        copyrightText: '© 2025 Dewei Zhai. Dit project valt onder de MIT-licentie.'
      }
    };
    function t(key) { return (L[currentLang] || L.en)[key] || L.en[key] || key; }
    function applyLanguage() {
      var langSel = document.getElementById('langSelect');
      currentLang = (langSel && langSel.value) || 'en';
      if (langSel) langSel.value = currentLang;
      localStorage.setItem('schools-lang', currentLang);
      var labelLanguage = document.getElementById('labelLanguage');
      if (labelLanguage) labelLanguage.textContent = t('labelLanguage');
      var countEl = document.getElementById('schoolCount');
      var count = countEl ? countEl.textContent : '0';
      document.title = t('titleMain');
      var titleMain = document.getElementById('titleMain');
      if (titleMain) titleMain.textContent = t('titleMain');
      var subtitleMain = document.getElementById('subtitleMain');
      if (subtitleMain) subtitleMain.innerHTML = t('subtitleBefore') + '<strong id="schoolCount">' + count + '</strong>' + t('subtitleAfter');
      var labelSchoolSearch = document.getElementById('labelSchoolSearch');
      if (labelSchoolSearch) labelSchoolSearch.textContent = t('labelSchoolSearch');
      var schoolSearch = document.getElementById('schoolSearch');
      if (schoolSearch) schoolSearch.placeholder = t('schoolSearchPlaceholder');
      var labelGemeente = document.getElementById('labelGemeente');
      if (labelGemeente) labelGemeente.textContent = t('labelGemeente');
      var gemeenteFilter = document.getElementById('gemeenteFilter');
      if (gemeenteFilter) gemeenteFilter.placeholder = t('gemeentePlaceholder');
      var labelLinear = document.getElementById('labelLinear');
      if (labelLinear) labelLinear.textContent = t('labelLinear');
      var labelLog = document.getElementById('labelLog');
      if (labelLog) labelLog.textContent = t('labelLog');
      var labelShowVMBO = document.getElementById('labelShowVMBO');
      if (labelShowVMBO) labelShowVMBO.textContent = t('labelShowVMBO');
      var labelSelectAll = document.getElementById('labelSelectAll');
      if (labelSelectAll) labelSelectAll.textContent = t('labelSelectAll');
      var labelDeselectAll = document.getElementById('labelDeselectAll');
      if (labelDeselectAll) labelDeselectAll.textContent = t('labelDeselectAll');
      var labelThemeEl = document.getElementById('labelTheme');
      if (labelThemeEl) labelThemeEl.textContent = t('labelTheme');
      var themeLightBtn = document.getElementById('themeLight');
      if (themeLightBtn) themeLightBtn.textContent = t('labelLight');
      var themeDarkBtn = document.getElementById('themeDark');
      if (themeDarkBtn) themeDarkBtn.textContent = t('labelDark');
      var excludedTitle = document.getElementById('excludedTitle');
      if (excludedTitle) excludedTitle.textContent = t('excludedTitle');
      var excludedDesc = document.getElementById('excludedDesc');
      if (excludedDesc) excludedDesc.textContent = t('excludedDesc');
      var algorithmTitle = document.getElementById('algorithmTitle');
      if (algorithmTitle) algorithmTitle.textContent = t('algorithmTitle');
      var algorithmBody = document.getElementById('algorithmBody');
      if (algorithmBody) algorithmBody.innerHTML = t('algorithmBody');
      var disclaimerTitle = document.getElementById('disclaimerTitle');
      if (disclaimerTitle) disclaimerTitle.textContent = t('disclaimerTitle');
      var disclaimerBody = document.getElementById('disclaimerBody');
      if (disclaimerBody) disclaimerBody.textContent = t('disclaimerBody');
      var contactTitle = document.getElementById('contactTitle');
      if (contactTitle) contactTitle.textContent = t('contactTitle');
      var supportHint = document.getElementById('supportHint');
      if (supportHint) supportHint.textContent = t('supportHint');
      var copyrightText = document.getElementById('copyrightText');
      if (copyrightText) copyrightText.textContent = t('copyrightText');
      if (typeof chart !== 'undefined') {
        var isLog = document.querySelector('input[name="coord"]:checked') && document.querySelector('input[name="coord"]:checked').value === 'log';
        chart.options.scales.x.title.text = isLog ? t('axisXLog') : t('axisXLinear');
        chart.options.scales.y.title.text = isLog ? t('axisYLog') : t('axisYLinear');
        chart.update();
      }
    }
    const linear = data.map(d => ({ x: d.X_linear, y: d.Y_linear, label: d.naam, type: d.type, gemeente: d.gemeente, size: d.size, brin: d.BRIN }));
    const log = data.map(d => ({ x: d.X_log, y: d.Y_log, label: d.naam, type: d.type, gemeente: d.gemeente, size: d.size, brin: d.BRIN }));

    let selectedGemeenten = new Set();
    var DEFAULT_GEMEENTEN = ["'S-GRAVENHAGE", 'AMSTERDAM', 'UTRECHT', 'ROTTERDAM'];

    function getPointsByTextFilter(points) {
      const parts = (document.getElementById('gemeenteFilter').value || '').split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
      if (parts.length === 0) return points;
      return points.filter(p => p.gemeente && parts.some(q => p.gemeente.toUpperCase().includes(q)));
    }
    function getFilteredPoints(points) {
      const byText = getPointsByTextFilter(points);
      /* 只显示勾选的 gemeenten：未勾选任何时显示为空，图例仅包含当前勾选项 */
      let result = byText.filter(p => p.gemeente && selectedGemeenten.has(p.gemeente));
      var showVMBOEl = document.getElementById('showVMBO');
      if (showVMBOEl && !showVMBOEl.checked) result = result.filter(function(p) { return p.type !== 'VMBO'; });
      return result;
    }
    function getGemeentenInList() {
      const coord = document.querySelector('input[name="coord"]:checked').value;
      const points = getPointsByTextFilter(coord === 'log' ? log : linear);
      const set = new Set();
      points.forEach(p => { if (p.gemeente) set.add(p.gemeente); });
      return Array.from(set).sort();
    }
    function renderGemeenteCheckboxes() {
      const list = getGemeentenInList();
      if (list.length > 0 && selectedGemeenten.size === 0) {
        var defaultSet = new Set(DEFAULT_GEMEENTEN);
        selectedGemeenten = new Set(list.filter(function(g) { return defaultSet.has(g); }));
        if (selectedGemeenten.size === 0) selectedGemeenten = new Set(list);
      }
      const container = document.getElementById('gemeenteCheckboxes');
      container.innerHTML = '';
      list.forEach(g => {
        const label = document.createElement('label');
        label.className = 'inline-flex items-center gap-2 cursor-pointer text-sm text-slate-600 hover:text-slate-800';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.className = 'gemeente-cb rounded border-slate-300 text-slate-600 focus:ring-slate-400';
        cb.dataset.gemeente = g;
        cb.checked = selectedGemeenten.has(g);
        cb.addEventListener('change', () => {
          if (cb.checked) selectedGemeenten.add(g); else selectedGemeenten.delete(g);
          syncSelectAllDeselectAll();
          refreshChart();
        });
        label.appendChild(cb);
        label.appendChild(document.createTextNode(g));
        container.appendChild(label);
      });
      syncSelectAllDeselectAll();
    }
    function syncSelectAllDeselectAll() {
      const list = getGemeentenInList();
      const allSelected = list.length > 0 && list.every(g => selectedGemeenten.has(g));
      const noneSelected = list.length === 0 || list.every(g => !selectedGemeenten.has(g));
      document.getElementById('selectAll').checked = allSelected;
      document.getElementById('deselectAll').checked = noneSelected;
    }
    function refreshChart() {
      const coord = document.querySelector('input[name="coord"]:checked').value;
      const points = getFilteredPoints(coord === 'log' ? log : linear);
      chart.data.datasets = makeDatasets(points);
      document.getElementById('schoolCount').textContent = points.length;
      chart.update();
    }

    /** 确定性 hash：gemeente 名字 -> 颜色。同一名字始终得到同一颜色。相似名字用黄金角+独立 S/L 拉开区分。 */
    function hashString(s, seed) {
      let h = seed || 0;
      const str = (s || '').toString().toUpperCase();
      for (let i = 0; i < str.length; i++) h = Math.imul(31, h) + str.charCodeAt(i) | 0;
      return Math.abs(h) >>> 0;
    }
    const GOLDEN = 137.508;
    function gemeenteToColor(gemeente) {
      const h = hashString(gemeente);
      const hS = hashString(gemeente, 1);
      const hL = hashString(gemeente, 2);
      const hue = (h * GOLDEN) % 360;
      const sat = 60 + (hS % 35);
      const light = 35 + (hL % 45);
      return `hsla(${hue}, ${sat}%, ${light}%, 0.9)`;
    }
    function gemeenteToBorderColor(gemeente) {
      const h = hashString(gemeente);
      const hS = hashString(gemeente, 1);
      const hL = hashString(gemeente, 2);
      const hue = (h * GOLDEN) % 360;
      const sat = Math.min(85, 60 + (hS % 35) + 10);
      const light = Math.max(18, 35 + (hL % 45) - 22);
      return `hsl(${hue}, ${sat}%, ${light}%)`;
    }

    /** 根据当前可见点的 size 将人数映射为圆点半径（约 4–20px） */
    function sizeToRadius(points) {
      const sizes = points.map(p => (p.size != null && p.size > 0) ? p.size : 0).filter(Boolean);
      if (sizes.length === 0) return () => 8;
      const minS = Math.min(...sizes);
      const maxS = Math.max(...sizes);
      const range = maxS - minS || 1;
      return function(size) {
        if (size == null || size <= 0) return 8;
        return Math.round(4 + 14 * (size - minS) / range);
      };
    }
    function getSchoolSearchTerm() {
      return (document.getElementById('schoolSearch') && document.getElementById('schoolSearch').value || '').trim().toUpperCase();
    }
    function pointMatchesSearch(p, searchTerm) {
      if (!searchTerm) return true;
      const naam = (p.label || '').toUpperCase();
      const brin = (p.brin || '').toUpperCase();
      const gemeente = (p.gemeente || '').toUpperCase();
      return naam.includes(searchTerm) || brin.includes(searchTerm) || gemeente.includes(searchTerm);
    }
    function makeDatasets(points) {
      const radiusFn = sizeToRadius(points);
      const searchTerm = getSchoolSearchTerm();
      const byGemeente = {};
      points.forEach(p => {
        const g = p.gemeente || '(未知)';
        if (!byGemeente[g]) byGemeente[g] = [];
        const matched = pointMatchesSearch(p, searchTerm);
        byGemeente[g].push({
          x: p.x, y: p.y, naam: p.label, type: p.type,
          r: radiusFn(p.size),
          size: p.size,
          matched: matched
        });
      });
      const gemeenten = Object.keys(byGemeente).sort();
      return gemeenten.map(g => {
        const bgColor = gemeenteToColor(g);
        return {
          label: g,
          data: byGemeente[g],
          pointRadius: function(ctx) {
            const r = ctx.raw.r != null ? ctx.raw.r : 8;
            return ctx.raw.matched ? Math.max(r, r * 1.4 + 2) : r;
          },
          backgroundColor: function(ctx) {
            if (ctx.raw.matched) return bgColor;
            return 'rgba(180,180,180,0.28)';
          },
          borderColor: function(ctx) {
            if (ctx.raw.matched) return bgColor;
            return 'rgba(120,120,120,0.45)';
          },
          borderWidth: 1
        };
      });
    }

    const chart = new Chart(document.getElementById('chart'), {
      type: 'scatter',
      data: { datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 4/3,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                const p = ctx.raw;
                const gemeente = ctx.dataset.label || '';
                const name = p.naam || '';
                let line = (gemeente ? gemeente + ' · ' : '') + name + ' — X: ' + p.x.toFixed(2) + ', Y: ' + p.y.toFixed(2);
                if (p.size != null && p.size > 0) line += ' · ' + t('tooltipCandidates') + ': ' + p.size;
                return line;
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'VWO share (%)' },
            min: -5,
            max: 105,
            grace: '0%',
            afterBuildTicks: function(axis) { axis.ticks = [0,10,20,30,40,50,60,70,80,90,100].map(function(v){ return { value: v }; }); },
            ticks: { stepSize: 10 }
          },
          y: {
            title: { display: true, text: 'Science share (%)' },
            min: -5,
            max: 105,
            grace: '0%',
            afterBuildTicks: function(axis) { axis.ticks = [0,10,20,30,40,50,60,70,80,90,100].map(function(v){ return { value: v }; }); },
            ticks: { stepSize: 10 }
          }
        }
      },
    });

    document.getElementById('selectAll').addEventListener('change', function() {
      if (this.checked) {
        const list = getGemeentenInList();
        selectedGemeenten = new Set(list);
        document.getElementById('deselectAll').checked = false;
        document.querySelectorAll('.gemeente-cb').forEach(cb => { cb.checked = true; });
      } else {
        selectedGemeenten = new Set();
        document.getElementById('deselectAll').checked = true;
        document.querySelectorAll('.gemeente-cb').forEach(cb => { cb.checked = false; });
      }
      syncSelectAllDeselectAll();
      refreshChart();
    });
    document.getElementById('deselectAll').addEventListener('change', function() {
      if (this.checked) {
        selectedGemeenten = new Set();
        document.getElementById('selectAll').checked = false;
        document.querySelectorAll('.gemeente-cb').forEach(cb => { cb.checked = false; });
      } else {
        const list = getGemeentenInList();
        selectedGemeenten = new Set(list);
        document.getElementById('selectAll').checked = true;
        document.querySelectorAll('.gemeente-cb').forEach(cb => { cb.checked = true; });
      }
      syncSelectAllDeselectAll();
      refreshChart();
    });

    document.getElementById('schoolSearch').addEventListener('input', refreshChart);
    document.getElementById('schoolSearch').addEventListener('change', refreshChart);

    document.getElementById('gemeenteFilter').addEventListener('input', function() {
      renderGemeenteCheckboxes();
      refreshChart();
    });
    document.getElementById('gemeenteFilter').addEventListener('change', function() {
      renderGemeenteCheckboxes();
      refreshChart();
    });

    var showVMBOEl = document.getElementById('showVMBO');
    if (showVMBOEl) showVMBOEl.addEventListener('change', refreshChart);

    document.getElementById('langSelect').addEventListener('change', function() {
      currentLang = this.value;
      localStorage.setItem('schools-lang', currentLang);
      applyLanguage();
    });
    document.getElementById('langSelect').value = currentLang;
    applyLanguage();

    function isDarkTheme() { return document.documentElement.classList.contains('dark'); }
    function updateChartTheme(dark) {
      var grid = dark ? '#475569' : '#e2e8f0';
      var text = dark ? '#e2e8f0' : '#334155';
      var tick = dark ? '#94a3b8' : '#64748b';
      if (chart && chart.options && chart.options.scales) {
        chart.options.scales.x.grid.color = grid;
        chart.options.scales.x.ticks.color = tick;
        chart.options.scales.x.title.color = text;
        chart.options.scales.y.grid.color = grid;
        chart.options.scales.y.ticks.color = tick;
        chart.options.scales.y.title.color = text;
        if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) chart.options.plugins.legend.labels.color = text;
        chart.update();
      }
    }
    function applyTheme(dark) {
      document.documentElement.classList.toggle('dark', dark);
      localStorage.setItem('theme', dark ? 'dark' : 'light');
      updateChartTheme(dark);
      var lightBtn = document.getElementById('themeLight');
      var darkBtn = document.getElementById('themeDark');
      if (lightBtn) { lightBtn.classList.toggle('bg-slate-200', !dark); lightBtn.classList.toggle('dark:bg-slate-600', dark); }
      if (darkBtn) { darkBtn.classList.toggle('bg-slate-200', dark); darkBtn.classList.toggle('dark:bg-slate-600', !dark); }
    }
    document.getElementById('themeLight').addEventListener('click', function() { applyTheme(false); });
    document.getElementById('themeDark').addEventListener('click', function() { applyTheme(true); });
    applyTheme(isDarkTheme());

    document.querySelectorAll('input[name="coord"]').forEach(radio => {
      radio.addEventListener('change', () => {
        const isLog = radio.value === 'log';
        chart.options.scales.x.title.text = isLog ? t('axisXLog') : t('axisXLinear');
        chart.options.scales.y.title.text = isLog ? t('axisYLog') : t('axisYLinear');
        if (isLog) {
          chart.options.scales.x.min = -0.02;
          chart.options.scales.x.max = 0.35;
          chart.options.scales.x.afterBuildTicks = undefined;
          chart.options.scales.x.ticks = { stepSize: 0.05 };
          chart.options.scales.y.min = -0.02;
          chart.options.scales.y.max = 0.35;
          chart.options.scales.y.afterBuildTicks = undefined;
          chart.options.scales.y.ticks = { stepSize: 0.05 };
        } else {
          chart.options.scales.x.min = -5;
          chart.options.scales.x.max = 105;
          chart.options.scales.x.afterBuildTicks = function(axis) { axis.ticks = [0,10,20,30,40,50,60,70,80,90,100].map(function(v){ return { value: v }; }); };
          chart.options.scales.x.ticks = { stepSize: 10 };
          chart.options.scales.y.min = -5;
          chart.options.scales.y.max = 105;
          chart.options.scales.y.afterBuildTicks = function(axis) { axis.ticks = [0,10,20,30,40,50,60,70,80,90,100].map(function(v){ return { value: v }; }); };
          chart.options.scales.y.ticks = { stepSize: 10 };
        }
        refreshChart();
      });
    });
    renderGemeenteCheckboxes();
    refreshChart();
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate school map HTML and optionally serve locally.")
    parser.add_argument("--static", action="store_true", help="Build only: write to public/index.html and exit (for Vercel static deploy).")
    args = parser.parse_args()

    if not os.path.exists(CSV_PATH):
        print(f"找不到 {CSV_PATH}，请先运行 calc_xy_coords.py", file=sys.stderr)
        return 1
    data = load_data()
    excluded = load_excluded()
    html = build_html(data, excluded)

    if args.static:
        out_dir = os.path.dirname(PUBLIC_INDEX)
        os.makedirs(out_dir, exist_ok=True)
        with open(PUBLIC_INDEX, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"已生成: {PUBLIC_INDEX}")
        return 0

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成: {HTML_PATH}")

    os.chdir(BASE)
    handler = SimpleHTTPRequestHandler
    server = HTTPServer(("", PORT), handler)
    url = f"http://127.0.0.1:{PORT}/view_xy.html"
    print(f"本地服务: {url}")
    webbrowser.open(url)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    exit(main() or 0)
