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
CSV_PATH_PO = os.path.join(BASE, "schools_xy_coords_po.csv")
EXCLUDED_PATH_PO = os.path.join(BASE, "excluded_schools_po.json")
HTML_PATH = os.path.join(BASE, "view_xy.html")
PUBLIC_INDEX = os.path.join(BASE, "public", "index.html")
PORT = 8082


def load_excluded(path=EXCLUDED_PATH):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def load_data_vo():
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            size_raw = r.get("candidates_total") or r.get("HAVO_geslaagd_total") or 0
            try:
                size = int(size_raw)
            except (ValueError, TypeError):
                size = 0
            rows.append({
                "BRIN": r["BRIN"],
                "naam": r["vestigingsnaam"],
                "gemeente": r["gemeente"],
                "postcode": (r.get("postcode") or "").strip(),
                "type": r["type"],
                "X_linear": float(r["X_linear"]),
                "Y_linear": float(r["Y_linear"]),
                "X_log": float(r["X_log"]),
                "Y_log": float(r["Y_log"]),
                "size": size,
            })
    return rows


def load_data_po():
    if not os.path.exists(CSV_PATH_PO):
        return []
    rows = []
    with open(CSV_PATH_PO, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            size_raw = r.get("pupils_total") or 0
            try:
                size = int(size_raw)
            except (ValueError, TypeError):
                size = 0
            rows.append({
                "BRIN": r["BRIN"],
                "naam": r["vestigingsnaam"],
                "gemeente": r["gemeente"],
                "postcode": (r.get("postcode") or "").strip(),
                "type": r["type"],
                "X_linear": float(r["X_linear"]),
                "Y_linear": float(r["Y_linear"]),
                "X_log": float(r["X_log"]),
                "Y_log": float(r["Y_log"]),
                "size": size,
            })
    return rows


def build_html(html_path, data_vo, excluded_vo, data_po, excluded_po):
    excluded_vo = excluded_vo if excluded_vo is not None else []
    excluded_po = excluded_po if excluded_po is not None else []
    data_vo_js = json.dumps(data_vo, ensure_ascii=False)
    data_po_js = json.dumps(data_po, ensure_ascii=False)
    excluded_vo_js = json.dumps(excluded_vo, ensure_ascii=False)
    excluded_po_js = json.dumps(excluded_po, ensure_ascii=False)
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__INJECT_DATA_VO__", data_vo_js)
    html = html.replace("__INJECT_DATA_PO__", data_po_js)
    html = html.replace("__INJECT_EXCLUDED_VO__", excluded_vo_js)
    html = html.replace("__INJECT_EXCLUDED_PO__", excluded_po_js)
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate school map HTML and optionally serve locally.")
    parser.add_argument("--static", action="store_true", help="Build only: write to public/index.html and exit (for Vercel static deploy).")
    args = parser.parse_args()

    if not os.path.exists(CSV_PATH):
        print(f"找不到 {CSV_PATH}，请先运行 calc_xy_coords.py", file=sys.stderr)
        return 1
    data_vo = load_data_vo()
    excluded_vo = load_excluded(EXCLUDED_PATH)
    data_po = load_data_po()
    excluded_po = load_excluded(EXCLUDED_PATH_PO)
    html = build_html(HTML_PATH, data_vo, excluded_vo, data_po, excluded_po)

    if args.static:
        out_dir = os.path.dirname(PUBLIC_INDEX)
        os.makedirs(out_dir, exist_ok=True)
        with open(PUBLIC_INDEX, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"已生成: {PUBLIC_INDEX}")
        return 0

    os.chdir(BASE)
    injected_html = html

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.rstrip("/") == "/view_xy.html":
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(injected_html.encode("utf-8"))
            else:
                super().do_GET()

    server = HTTPServer(("", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/view_xy.html"
    print(f"本地服务: {url} （仅维护 view_xy.html，数据由服务注入）")
    webbrowser.open(url)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    exit(main() or 0)
