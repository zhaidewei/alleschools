from pathlib import Path

from alleschools import config, etl


EXPECTED_YEAR_COLS = [
    [13, 14, "2020-2021", 0.2],
    [22, 23, "2021-2022", 0.4],
    [31, 32, "2022-2023", 0.6],
    [40, 41, "2023-2024", 0.8],
    [49, 50, "2024-2025", 1.0],
]


def test_vo_exam_window_matches_profile_score_window() -> None:
    cfg = config.build_effective_config()

    assert cfg["vo"]["weights"]["year_cols"] == EXPECTED_YEAR_COLS


def test_fetch_vo_exams_uses_latest_five_year_file(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_download(url: str, out_path: Path) -> Path:
        captured["url"] = url
        captured["out_path"] = out_path
        return out_path

    monkeypatch.setattr(etl, "_download_atomic", fake_download)

    result = etl.fetch_vo_exams(tmp_path)

    assert captured["url"].endswith("examenkandidaten-en-geslaagden-2020-2025.csv")
    assert captured["out_path"] == tmp_path / "duo_examen_raw_all.csv"
    assert result == captured["out_path"]
