#!/usr/bin/env python3
"""
读取 schools_xy_coords.csv，生成带散点图的 HTML，并在本地启动 HTTP 服务。
浏览器打开后显示：横轴 VWO 通过人数占比，纵轴 理科占比；可切换线性/对数坐标。
"""
import csv
import json
import os
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "schools_xy_coords.csv")
EXCLUDED_PATH = os.path.join(BASE, "excluded_schools.json")
HTML_PATH = os.path.join(BASE, "view_xy.html")
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
  <title>学校坐标：VWO通过人数占比 × 理科占比</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    tailwind.config = { theme: { extend: { fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] } } } }
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body class="min-h-screen bg-slate-50 text-slate-800 font-sans antialiased">
  <div id="wrap" class="max-w-6xl mx-auto px-4 sm:px-6 py-8">
    <div id="chartWrap" class="mb-8">
      <h1 class="text-xl font-semibold text-slate-800 tracking-tight">学校坐标：VWO通过人数占比（横轴）× 理科占比（纵轴）</h1>
      <p class="mt-1 text-sm text-slate-500">数据来自 DUO 考试人数，近年权重更高。VMBO 学校仅作参考（X=0）。共 <strong id="schoolCount" class="font-medium text-slate-700">0</strong> 所学校。</p>
      <div class="mt-4 bg-white rounded-xl border border-slate-200/80 shadow-sm p-4 sm:p-6">
        <div class="w-full aspect-[4/3] min-h-[420px]">
          <canvas id="chart" class="w-full h-full block"></canvas>
        </div>
      </div>
    </div>
    <div class="controls flex flex-wrap items-center gap-4 sm:gap-6 py-4 px-4 bg-white rounded-xl border border-slate-200/80 shadow-sm">
      <div class="flex items-center gap-2">
        <label class="text-sm font-medium text-slate-600 whitespace-nowrap">学校搜索</label>
        <input type="text" id="schoolSearch" placeholder="按校名或 BRIN 搜索，匹配项高亮" class="flex-1 min-w-[200px] rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400">
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm font-medium text-slate-600 whitespace-nowrap">Gemeente 过滤</label>
        <input type="text" id="gemeenteFilter" placeholder="不输入显示全部，多个用逗号分隔" class="flex-1 min-w-[180px] rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400">
      </div>
      <div class="flex flex-wrap items-center gap-4">
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm text-slate-600">
          <input type="radio" name="coord" value="linear" checked class="rounded-full border-slate-300 text-slate-600 focus:ring-slate-400">
          <span>线性坐标</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm text-slate-600">
          <input type="radio" name="coord" value="log" class="rounded-full border-slate-300 text-slate-600 focus:ring-slate-400">
          <span>对数坐标</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm text-slate-600">
          <input type="checkbox" id="showVMBO" class="rounded border-slate-300 text-slate-600 focus:ring-slate-400">
          <span>显示纯 VMBO 学校</span>
        </label>
      </div>
    </div>
    <div id="gemeenteList" class="mt-8 pt-6 border-t border-slate-200">
      <div class="gemeente-list-header flex flex-wrap items-center gap-4 mb-3">
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm font-medium text-slate-600">
          <input type="checkbox" id="selectAll" class="rounded border-slate-300 text-slate-600 focus:ring-slate-400">
          <span>全选</span>
        </label>
        <label class="inline-flex items-center gap-2 cursor-pointer text-sm font-medium text-slate-600">
          <input type="checkbox" id="deselectAll" class="rounded border-slate-300 text-slate-600 focus:ring-slate-400">
          <span>全部取消</span>
        </label>
      </div>
      <div id="gemeenteCheckboxes" class="max-h-56 overflow-y-auto flex flex-wrap gap-x-4 gap-y-2"></div>
    </div>
    <div id="excludedSection" class="mt-8 pt-6 border-t border-slate-200 text-sm text-slate-500"></div>
  </div>
  <script>
    (function() {
      const excluded = """ + excluded_js + """;
      const el = document.getElementById('excludedSection');
      if (excluded.length === 0) { el.innerHTML = ''; return; }
      el.innerHTML = '<h2 class="text-base font-semibold text-slate-700 mb-2">因数据点过少未纳入图表的学校</h2><p class="mb-3 text-slate-500">以下学校因 HAVO/VWO 考生数过少（5 年合计 &lt; 20）未参与坐标计算，故未出现在上图中。</p><ul class="list-disc pl-5 max-h-44 overflow-y-auto space-y-1 text-slate-600">' +
        excluded.map(function(s) { return '<li>' + (s.BRIN || '') + ' ' + (s.naam || '') + ' (' + (s.gemeente || '') + ')</li>'; }).join('') + '</ul>';
    })();
  </script>
  <script>
    const data = """ + data_js + """;
    const linear = data.map(d => ({ x: d.X_linear, y: d.Y_linear, label: d.naam, type: d.type, gemeente: d.gemeente, size: d.size, brin: d.BRIN }));
    const log = data.map(d => ({ x: d.X_log, y: d.Y_log, label: d.naam, type: d.type, gemeente: d.gemeente, size: d.size, brin: d.BRIN }));

    let selectedGemeenten = new Set();

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
      if (list.length > 0 && selectedGemeenten.size === 0) selectedGemeenten = new Set(list);
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
        const borderColorVal = gemeenteToBorderColor(g);
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
            if (ctx.raw.matched) return borderColorVal;
            return 'rgba(160,160,160,0.4)';
          },
          borderWidth: function(ctx) { return ctx.raw.matched ? 2.5 : 1; }
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
                if (p.size != null && p.size > 0) line += ' · 5年考生: ' + p.size;
                return line;
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'VWO 通过人数占比 (%) — 100% 学术性最强' },
            min: -5,
            max: 105,
            grace: '0%',
            afterBuildTicks: function(axis) { axis.ticks = [0,10,20,30,40,50,60,70,80,90,100].map(function(v){ return { value: v }; }); },
            ticks: { stepSize: 10 }
          },
          y: {
            title: { display: true, text: '理科占比 (%)' },
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

    document.querySelectorAll('input[name="coord"]').forEach(radio => {
      radio.addEventListener('change', () => {
        const isLog = radio.value === 'log';
        chart.options.scales.x.title.text = isLog ? 'VWO 通过人数占比 (log10(1+x/100))' : 'VWO 通过人数占比 (%) — 100% 学术性最强';
        chart.options.scales.y.title.text = isLog ? '理科占比 (log10(1+y/100))' : '理科占比 (%)';
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
    if not os.path.exists(CSV_PATH):
        print(f"找不到 {CSV_PATH}，请先运行 calc_xy_coords.py")
        return 1
    data = load_data()
    excluded = load_excluded()
    html = build_html(data, excluded)
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


if __name__ == "__main__":
    exit(main() or 0)
