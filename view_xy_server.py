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
RUN_REPORT_PO = os.path.join(BASE, "run_report_po.json")
RUN_REPORT_VO = os.path.join(BASE, "run_report_vo.json")
HTML_PATH = os.path.join(BASE, "view_xy.html")
PUBLIC_INDEX = os.path.join(BASE, "public", "index.html")
DEMO_DIR = os.path.join(BASE, "demo")
DEMO_INDEX = os.path.join(DEMO_DIR, "datasets_index.json")
PORT = 8082


def _load_run_report(path, kind):
    """
    读取 run_report_po.json / run_report_vo.json，并返回给定 kind（'po' 或 'vo'）的 outputs 子树。
    若文件不存在或结构异常，则返回空 dict，调用方可回退到默认路径。
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if isinstance(data, list):
        if not data:
            return {}
        data = data[0]
    if not isinstance(data, dict):
        return {}
    return data.get("outputs", {}).get(kind, {}) or {}


def _get_vo_paths():
    """
    从 run_report_vo.json 推断 VO 的 csv/excluded/points/meta 路径。
    若缺失则回退到旧的常量路径。
    """
    d = _load_run_report(RUN_REPORT_VO, "vo")

    # run_report 中可能记录了本地机器的绝对路径；统一转换为相对仓库根目录的路径。
    raw_csv = d.get("csv_path")
    if raw_csv and os.path.isabs(raw_csv):
        raw_csv = os.path.join(BASE, os.path.basename(raw_csv))
    raw_excluded = d.get("excluded_path")
    if raw_excluded and os.path.isabs(raw_excluded):
        raw_excluded = os.path.join(BASE, os.path.basename(raw_excluded))

    csv_path = raw_csv or CSV_PATH
    excluded_path = raw_excluded or EXCLUDED_PATH

    # 在 CI / Vercel 等环境下，如果记录的路径不存在，则回退到默认 CSV/JSON。
    if not os.path.exists(csv_path) and os.path.exists(CSV_PATH):
        csv_path = CSV_PATH
    if not os.path.exists(excluded_path) and os.path.exists(EXCLUDED_PATH):
        excluded_path = EXCLUDED_PATH

    return {
        "csv_path": csv_path,
        "excluded_path": excluded_path,
        "points_path": d.get("points_path") or None,
        "meta_path": d.get("meta_path") or None,
    }


def _get_po_paths():
    """
    从 run_report_po.json 推断 PO 的 csv/excluded/points/meta 路径。
    若缺失则回退到旧的常量路径。
    """
    d = _load_run_report(RUN_REPORT_PO, "po")

    raw_csv = d.get("csv_path")
    if raw_csv and os.path.isabs(raw_csv):
        raw_csv = os.path.join(BASE, os.path.basename(raw_csv))
    raw_excluded = d.get("excluded_path")
    if raw_excluded and os.path.isabs(raw_excluded):
        raw_excluded = os.path.join(BASE, os.path.basename(raw_excluded))

    csv_path = raw_csv or CSV_PATH_PO
    excluded_path = raw_excluded or EXCLUDED_PATH_PO

    if not os.path.exists(csv_path) and os.path.exists(CSV_PATH_PO):
        csv_path = CSV_PATH_PO
    if not os.path.exists(excluded_path) and os.path.exists(EXCLUDED_PATH_PO):
        excluded_path = EXCLUDED_PATH_PO

    return {
        "csv_path": csv_path,
        "excluded_path": excluded_path,
        "points_path": d.get("points_path") or None,
        "meta_path": d.get("meta_path") or None,
    }


def load_excluded(path=EXCLUDED_PATH):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def load_data_vo():
    """从正式 VO CSV 加载图表数据。"""
    paths = _get_vo_paths()
    csv_path = paths["csv_path"]
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            size_raw = r.get("candidates_total") or r.get("HAVO_geslaagd_total") or 0
            try:
                size = int(size_raw)
            except (ValueError, TypeError):
                size = 0
            rows.append(
                {
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
                }
            )
    return rows


def load_data_po():
    """从正式 PO CSV 加载图表数据。"""
    paths = _get_po_paths()
    csv_path = paths["csv_path"]
    if not os.path.exists(csv_path):
        return []
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            size_raw = r.get("pupils_total") or 0
            try:
                size = int(size_raw)
            except (ValueError, TypeError):
                size = 0
            rows.append(
                {
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
                }
            )
    return rows


def _load_demo_index():
    """加载 demo/datasets_index.json。"""
    if not os.path.exists(DEMO_INDEX):
        raise FileNotFoundError(f"demo index not found: {DEMO_INDEX}")
    with open(DEMO_INDEX, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_demo_points(layer: str):
    """从 demo points JSON 加载某个 layer（vo/po）的 points 列表。"""
    idx = _load_demo_index()
    ds = idx.get("datasets", {}).get(layer)
    if not ds:
        raise KeyError(f"no demo dataset for layer={layer!r} in {DEMO_INDEX}")
    data_path = os.path.join(DEMO_DIR, ds["data_path"])
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_demo_meta(layer: str):
    """从 demo meta JSON 加载某个 layer（vo/po）的 meta 对象。"""
    idx = _load_demo_index()
    ds = idx.get("datasets", {}).get(layer)
    if not ds:
        raise KeyError(f"no demo dataset for layer={layer!r} in {DEMO_INDEX}")
    meta_path = os.path.join(DEMO_DIR, ds["meta_path"])
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_demo_data():
    """
    使用 demo/ 下的 JSON（遵守 refactor/SCHEMA.md）加载 VO/PO 数据，
    并转换为旧前端脚本期望的字段形状。
    """
    # PO
    po_points = _load_demo_points("po")
    po_meta = _load_demo_meta("po")
    data_po = []
    for p in po_points:
        data_po.append(
            {
                "BRIN": p.get("brin") or p.get("id"),
                "naam": p.get("name", ""),
                "gemeente": p.get("municipality", ""),
                "postcode": (p.get("postcode") or "").strip(),
                "type": p.get("school_type", ""),
                "X_linear": float(p.get("x_linear", 0.0)),
                "Y_linear": float(p.get("y_linear", 0.0)),
                "X_log": float(p.get("x_log", 0.0)),
                "Y_log": float(p.get("y_log", 0.0)),
                "size": int(p.get("size") or 0),
            }
        )

    # VO（如果 demo 中暂时没有，可以回退为空列表）
    try:
        vo_points = _load_demo_points("vo")
        vo_meta = _load_demo_meta("vo")
    except (FileNotFoundError, KeyError):
        vo_points = []
        vo_meta = {}
    data_vo = []
    for p in vo_points:
        data_vo.append(
            {
                "BRIN": p.get("brin") or p.get("id"),
                "naam": p.get("name", ""),
                "gemeente": p.get("municipality", ""),
                "postcode": (p.get("postcode") or "").strip(),
                "type": p.get("school_type", ""),
                "X_linear": float(p.get("x_linear", 0.0)),
                "Y_linear": float(p.get("y_linear", 0.0)),
                "X_log": float(p.get("x_log", 0.0)),
                "Y_log": float(p.get("y_log", 0.0)),
                "size": int(p.get("size") or 0),
            }
        )

    # demo 模式下暂不提供排除列表，保持为空
    return data_vo, [], data_po, [], vo_meta, po_meta


def build_html(html_path, data_vo, excluded_vo, data_po, excluded_po, meta_vo=None, meta_po=None):
    excluded_vo = excluded_vo if excluded_vo is not None else []
    excluded_po = excluded_po if excluded_po is not None else []
    meta_vo = meta_vo if meta_vo is not None else {}
    meta_po = meta_po if meta_po is not None else {}
    data_vo_js = json.dumps(data_vo, ensure_ascii=False)
    data_po_js = json.dumps(data_po, ensure_ascii=False)
    excluded_vo_js = json.dumps(excluded_vo, ensure_ascii=False)
    excluded_po_js = json.dumps(excluded_po, ensure_ascii=False)
    meta_vo_js = json.dumps(meta_vo, ensure_ascii=False)
    meta_po_js = json.dumps(meta_po, ensure_ascii=False)
    print(f"[view_xy_server] 使用 HTML 模板: {html_path}", file=sys.stderr)
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__INJECT_DATA_VO__", data_vo_js)
    html = html.replace("__INJECT_DATA_PO__", data_po_js)
    html = html.replace("__INJECT_EXCLUDED_VO__", excluded_vo_js)
    html = html.replace("__INJECT_EXCLUDED_PO__", excluded_po_js)
    html = html.replace("__INJECT_META_VO__", meta_vo_js)
    html = html.replace("__INJECT_META_PO__", meta_po_js)
    return html


def main():
    parser = argparse.ArgumentParser(
        description="Generate school map HTML and optionally serve locally."
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Build only: write to public/index.html and exit (for Vercel static deploy).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use demo JSON datasets from demo/ (following refactor/SCHEMA.md) instead of CSV.",
    )
    args = parser.parse_args()

    if args.demo:
        try:
            data_vo, excluded_vo, data_po, excluded_po, meta_vo, meta_po = load_demo_data()
        except Exception as e:  # pragma: no cover - 简单错误提示即可
            print(f"加载 demo 数据失败: {e}", file=sys.stderr)
            return 1
    else:
        vo_paths = _get_vo_paths()
        vo_csv = vo_paths["csv_path"]
        if not os.path.exists(vo_csv):
            print(f"找不到 {vo_csv}，请先运行 python -m alleschools.cli vo", file=sys.stderr)
            return 1
        data_vo = load_data_vo()
        excluded_vo = load_excluded(_get_vo_paths()["excluded_path"])
        data_po = load_data_po()
        excluded_po = load_excluded(_get_po_paths()["excluded_path"])
        meta_vo = {}
        meta_po = {}

    html = build_html(HTML_PATH, data_vo, excluded_vo, data_po, excluded_po, meta_vo, meta_po)

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
            # 忽略查询参数，仅按路径匹配，确保带 ? 的 URL 也能得到注入后的 HTML
            path_only = self.path.split("?", 1)[0].rstrip("/")
            if path_only == "/view_xy.html":
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(injected_html.encode("utf-8"))
            else:
                super().do_GET()

    server = HTTPServer(("", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/view_xy.html"
    mode = "demo JSON" if args.demo else "CSV"
    print(f"本地服务: {url} （数据来源: {mode}）")
    webbrowser.open(url)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    exit(main() or 0)
