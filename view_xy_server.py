#!/usr/bin/env python3
"""
读取 schools_xy_coords.csv，生成带散点图的 HTML，并在本地启动 HTTP 服务。
浏览器打开后显示：横轴 VWO 占比，纵轴 理科占比；可切换线性/对数坐标。
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
            rows.append({
                "BRIN": r["BRIN"],
                "naam": r["vestigingsnaam"],
                "gemeente": r["gemeente"],
                "type": r["type"],
                "X_linear": float(r["X_linear"]),
                "Y_linear": float(r["Y_linear"]),
                "X_log": float(r["X_log"]),
                "Y_log": float(r["Y_log"]),
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
  <title>学校坐标：VWO占比 × 理科占比</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: system-ui, sans-serif; margin: 24px; background: #f8f9fa; }
    h1 { font-size: 1.25rem; }
    #wrap { max-width: 720px; }
    #chartWrap { margin-bottom: 20px; }
    canvas { background: #fff; border-radius: 8px; display: block; }
    .controls { margin: 16px 0; }
    .controls label { margin-right: 12px; }
    #gemeenteList { margin-top: 16px; border-top: 1px solid #ddd; padding-top: 12px; }
    .gemeente-list-header { margin-bottom: 8px; font-weight: 600; }
    .gemeente-list-header label { margin-right: 16px; cursor: pointer; font-weight: normal; }
    #gemeenteCheckboxes { max-height: 240px; overflow-y: auto; display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 8px; }
    #gemeenteCheckboxes label { cursor: pointer; font-weight: normal; display: inline-flex; align-items: center; gap: 4px; }
    #excludedSection { margin-top: 24px; padding-top: 16px; border-top: 1px solid #ddd; color: #555; font-size: 0.9rem; }
    #excludedSection h2 { font-size: 1rem; margin-bottom: 8px; }
    #excludedSection ul { margin: 0; padding-left: 20px; max-height: 180px; overflow-y: auto; }
  </style>
</head>
<body>
  <div id="wrap">
    <div id="chartWrap">
      <h1>学校坐标：VWO占比（横轴）× 理科占比（纵轴）</h1>
      <p style="color:#666; font-size:0.9rem;">数据来自 DUO 考试人数，近年权重更高。VMBO 学校仅作参考（X=0）。共 <strong id="schoolCount">0</strong> 所学校。</p>
      <canvas id="chart" width="700" height="420"></canvas>
    </div>
    <div class="controls">
      <label>Gemeente 过滤: <input type="text" id="gemeenteFilter" placeholder="不输入显示全部，多个用逗号分隔" style="margin-right:12px;"></label>
      <label><input type="radio" name="coord" value="linear" checked> 线性坐标</label>
      <label><input type="radio" name="coord" value="log"> 对数坐标</label>
    </div>
    <div id="gemeenteList">
      <div class="gemeente-list-header">
        <label><input type="checkbox" id="selectAll"> 全选</label>
        <label><input type="checkbox" id="deselectAll"> 全部取消</label>
      </div>
      <div id="gemeenteCheckboxes"></div>
    </div>
    <div id="excludedSection"></div>
  </div>
  <script>
    (function() {
      const excluded = """ + excluded_js + """;
      const el = document.getElementById('excludedSection');
      if (excluded.length === 0) { el.innerHTML = ''; return; }
      el.innerHTML = '<h2>因数据点过少未纳入图表的学校</h2><p style="margin-bottom:8px;">以下学校因 HAVO/VWO 考生数过少（5 年合计 &lt; 20）未参与坐标计算，故未出现在上图中。</p><ul>' +
        excluded.map(function(s) { return '<li>' + (s.BRIN || '') + ' ' + (s.naam || '') + ' (' + (s.gemeente || '') + ')</li>'; }).join('') + '</ul>';
    })();
  </script>
  <script>
    const data = """ + data_js + """;
    const linear = data.map(d => ({ x: d.X_linear, y: d.Y_linear, label: d.naam, type: d.type, gemeente: d.gemeente }));
    const log = data.map(d => ({ x: d.X_log, y: d.Y_log, label: d.naam, type: d.type, gemeente: d.gemeente }));

    let selectedGemeenten = new Set();

    function getPointsByTextFilter(points) {
      const parts = (document.getElementById('gemeenteFilter').value || '').split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
      if (parts.length === 0) return points;
      return points.filter(p => p.gemeente && parts.some(q => p.gemeente.toUpperCase().includes(q)));
    }
    function getFilteredPoints(points) {
      const byText = getPointsByTextFilter(points);
      if (selectedGemeenten.size === 0) return [];
      return byText.filter(p => p.gemeente && selectedGemeenten.has(p.gemeente));
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
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.className = 'gemeente-cb';
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

    function makeDatasets(points) {
      const byGemeente = {};
      points.forEach(p => {
        const g = p.gemeente || '(未知)';
        if (!byGemeente[g]) byGemeente[g] = [];
        byGemeente[g].push({ x: p.x, y: p.y, naam: p.label, type: p.type });
      });
      const gemeenten = Object.keys(byGemeente).sort();
      return gemeenten.map(g => ({
        label: g,
        data: byGemeente[g],
        pointRadius: 8,
        backgroundColor: gemeenteToColor(g),
        borderColor: gemeenteToBorderColor(g),
        borderWidth: 1
      }));
    }

    const chart = new Chart(document.getElementById('chart'), {
      type: 'scatter',
      data: {
        datasets: makeDatasets(getFilteredPoints(linear))
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 700/420,
        plugins: {
          legend: { position: 'top' },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                const p = ctx.raw;
                const gemeente = ctx.dataset.label || '';
                const name = p.naam || '';
                return (gemeente ? gemeente + ' · ' : '') + name + ' — X: ' + p.x.toFixed(2) + ', Y: ' + p.y.toFixed(2);
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'VWO 占比 (%) — 100% 学术性最强' },
            min: 0,
            max: 105,
            grace: '0%',
            ticks: { min: 0, max: 105, stepSize: 21 }
          },
          y: {
            title: { display: true, text: '理科占比 (%)' },
            min: 0,
            max: 105,
            grace: '0%',
            ticks: { min: 0, max: 105, stepSize: 21 }
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

    document.getElementById('gemeenteFilter').addEventListener('input', function() {
      renderGemeenteCheckboxes();
      refreshChart();
    });
    document.getElementById('gemeenteFilter').addEventListener('change', function() {
      renderGemeenteCheckboxes();
      refreshChart();
    });

    document.querySelectorAll('input[name="coord"]').forEach(radio => {
      radio.addEventListener('change', () => {
        const isLog = radio.value === 'log';
        chart.options.scales.x.title.text = isLog ? 'VWO 占比 (log10(1+x/100))' : 'VWO 占比 (%) — 100% 学术性最强';
        chart.options.scales.y.title.text = isLog ? '理科占比 (log10(1+y/100))' : '理科占比 (%)';
        if (isLog) {
          chart.options.scales.x.min = 0;
          chart.options.scales.x.max = 0.35;
          chart.options.scales.x.ticks = { min: 0, max: 0.35, stepSize: 0.05 };
          chart.options.scales.y.min = 0;
          chart.options.scales.y.max = 0.35;
          chart.options.scales.y.ticks = { min: 0, max: 0.35, stepSize: 0.05 };
        } else {
          chart.options.scales.x.min = 0;
          chart.options.scales.x.max = 105;
          chart.options.scales.x.ticks = { min: 0, max: 105, stepSize: 21 };
          chart.options.scales.y.min = 0;
          chart.options.scales.y.max = 105;
          chart.options.scales.y.ticks = { min: 0, max: 105, stepSize: 21 };
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
