from __future__ import annotations

"""
Loader for DUO "examenkandidaten vwo en examencijfers" CSVs.

Goal for the first iteration of the VO VWO‑median feature:

- Read one or more DUO per‑subject VWO exam CSV files.
- Aggregate, per vestiging (school location), the list of subject‑level
  final marks ("GEM  CIJFER CIJFERLIJST") for VWO pupils.
- Return a structure that later compute functions can turn into:
  - per‑year school medians; and
  - optionally time‑aggregated indicators.

We keep the loader purely IO/row‑level; no statistics here.
"""

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional


# DUO column names used in the VWO exam CSVs
COL_SCHOOLJAAR = "SCHOOLJAAR"
COL_INSTELLINGSCODE = "INSTELLINGSCODE"
COL_VESTIGINGSCODE = "VESTIGINGSCODE"
# 部分 DUO 文件使用以下列名（与 INSTELLINGSCODE/VESTIGINGSCODE 等价）
COL_BRIN_NUMMER = "BRIN NUMMER"
COL_VESTIGINGSNUMMER = "VESTIGINGSNUMMER"
COL_INSTELLINGSNAAM_VESTIGING = "INSTELLINGSNAAM VESTIGING"
COL_GEMEENTENAAM = "GEMEENTENAAM"
COL_ONDERWIJSTYPE_VO = "ONDERWIJSTYPE VO"
COL_VAK_AFKORTING = "AFKORTING VAKNAAM"
COL_VAKNAAM = "VAKNAAM"
COL_GEM_CIJFER_CIJFERLIJST = "GEM  CIJFER CIJFERLIJST"
COL_GEM_CE_MEETELLEND = "GEM  CIJFER CENTRALE EXAMENS MET CIJFER MEETELLEND VOOR DIPLOMA"
COL_GEM_CE_TOTAAL = "GEM  CIJFER TOTAAL AANTAL CENTRALE EXAMENS"
# DUO 部分 CSV 使用 "GEM."（带点）而非 "GEM  "（双空格）
COL_GEM_CE_MEETELLEND_ALT = "GEM. CIJFER CENTRALE EXAMENS MET CIJFER MEETELLEND VOOR DIPLOMA"
COL_GEM_CE_TOTAAL_ALT = "GEM. CIJFER TOTAAL AANTAL CENTRALE EXAMENS"


def _parse_float_nl(s: Optional[str]) -> Optional[float]:
    """
    Parse a Dutch style decimal string (comma as decimal separator) to float.

    Returns None when the cell is empty, contains only formatting
    artifacts like ",0", or is non‑numeric.
    """
    if s is None:
        return None
    raw = s.strip().strip('"')
    if not raw:
        return None
    # DUO often uses ",0" for "no value"; treat as missing rather than 0.0
    if raw in {",0", "0,0"}:
        return None
    # Replace decimal comma with dot
    raw = raw.replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        return None
    # Defensive: ignore obviously invalid / sentinel values
    if value <= 0.0:
        return None
    return value


def _is_vwo_row(row: Mapping[str, str]) -> bool:
    """Return True for rows that represent VWO exam results."""
    otype = (row.get(COL_ONDERWIJSTYPE_VO) or "").strip().strip('"').upper()
    return otype == "VWO"


def _brin_key_from_row(row: Mapping[str, str]) -> str:
    """
    Construct a BRIN/vestiging key that matches the main VO pipeline (e.g. 6 digits like "00AH00").

    DUO VWO 统考 CSV 可能使用以下列名组合:
    - INSTELLINGSCODE (e.g. "00AH") + VESTIGINGSCODE (e.g. "00") -> "00AH00"
    - 或旧格式: BRIN NUMMER + VESTIGINGSNUMMER

    主 VO 宽表 BRIN 为 INSTELLINGSCODE + VESTIGINGSCODE 拼接。
    """
    # 优先使用 INSTELLINGSCODE + VESTIGINGSCODE（当前 DUO 2024-2025 等文件使用）
    inst = (row.get(COL_INSTELLINGSCODE) or "").strip().strip('"')
    vest = (row.get(COL_VESTIGINGSCODE) or "").strip().strip('"')
    if inst and vest:
        return (inst + vest).replace(" ", "")
    # 回退到 BRIN NUMMER + VESTIGINGSNUMMER
    brin = (row.get(COL_BRIN_NUMMER) or "").strip().strip('"')
    vestnr = (row.get(COL_VESTIGINGSNUMMER) or "").strip().strip('"')
    if brin and vestnr:
        return (brin + vestnr).replace(" ", "")
    return vest


@dataclass
class SchoolYearScores:
    """
    Container for per‑school, per‑year VWO subject‑level scores.

    For now we only store:
    - a flat list of cijferlijst scores per year, ready for median/other stats.
    """

    naam: str
    gemeente: str
    # year_label (e.g. "2021-2022") -> list of final marks for that year
    years: MutableMapping[str, List[float]] = field(default_factory=dict)


@dataclass
class SchoolYearCentralExamScores:
    """
    Container for per‑school, per‑year VWO central exam subject averages.

    years[year_label][subject_code] = central exam average (1–10),
    where subject_code is based on DUO's AFKORTING VAKNAAM (uppercased).
    """

    naam: str
    gemeente: str
    years: MutableMapping[str, Dict[str, float]] = field(default_factory=dict)


def load_vwo_exam_cijferlijst_scores(
    base_dir: str,
    schoolyear_files: Mapping[str, str],
) -> Dict[str, SchoolYearScores]:
    """
    Load DUO per‑subject VWO exam CSVs and aggregate cijferlijst scores by school.

    Parameters
    ----------
    base_dir:
        Directory where the CSV files live (typically the raw data root).
    schoolyear_files:
        Mapping from a logical schoolyear label (e.g. "2020-2021") to a
        CSV filename (relative to `base_dir`), e.g.:

            {
                "2020-2021": "examenkandidaten-vwo-en-examencijfers-2020-2021.csv",
                "2021-2022": "examenkandidaten-vwo-en-examencijfers-2021-2022.csv",
                ...
            }

    Returns
    -------
    dict
        A mapping brin -> SchoolYearScores, where "brin" in this context
        follows the existing VO pipeline convention and equals the
        `VESTIGINGSCODE` from DUO files (assumed globally unique).

    Notes
    -----
    - Only rows with `ONDERWIJSTYPE VO == "VWO"` are considered.
    - Only strictly positive `GEM  CIJFER CIJFERLIJST` values are kept.
    - We do not yet apply any filtering by subject type or candidate count;
      higher‑level compute code is responsible for that.
    """
    schools: Dict[str, SchoolYearScores] = {}

    for year_label, filename in schoolyear_files.items():
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            # Silently skip missing files; caller can inspect resulting years.
            continue

        # DUO typically uses semicolon‑separated CSV with latin‑1 compatible text,
        # but a robust loader should try UTF‑8 first.
        rows: Iterable[Mapping[str, str]] = ()
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                with open(path, "r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f, delimiter=";", quotechar='"')
                    rows = list(reader)
                break
            except UnicodeDecodeError:
                continue
        else:
            # All encodings failed; skip this year.
            continue

        for row in rows:
            if not _is_vwo_row(row):
                continue

            vest = _brin_key_from_row(row)
            if not vest:
                # We rely on vestigingscode to align with the rest of the VO pipeline.
                continue

            naam = (row.get(COL_INSTELLINGSNAAM_VESTIGING) or "").strip().strip('"')
            gemeente = (row.get(COL_GEMEENTENAAM) or "").strip().strip('"')

            cijfer = _parse_float_nl(row.get(COL_GEM_CIJFER_CIJFERLIJST))
            if cijfer is None:
                continue

            if vest not in schools:
                schools[vest] = SchoolYearScores(naam=naam, gemeente=gemeente)

            year_scores = schools[vest].years.setdefault(year_label, [])
            year_scores.append(cijfer)

    return schools


def load_vwo_central_exam_scores(
    base_dir: str,
    schoolyear_files: Mapping[str, str],
) -> Dict[str, SchoolYearCentralExamScores]:
    """
    Load DUO per‑subject VWO exam CSVs and aggregate central exam averages by school.

    This is tailored for the profiel indices in VO backlog 3.5:
    we focus on central exam averages per subject and per year, for VWO pupils.

    For each school (vestiging) and schoolyear we keep a mapping:

        subject_code (AFKORTING VAKNAAM, uppercased) -> C(vak) in [1, 10]

    C(vak) uses:
    - `GEM  CIJFER CENTRALE EXAMENS MET CIJFER MEETELLEND VOOR DIPLOMA`
      when available (preferred);
    - otherwise falls back to `GEM  CIJFER TOTAAL AANTAL CENTRALE EXAMENS`.
    """
    schools: Dict[str, SchoolYearCentralExamScores] = {}

    for year_label, filename in schoolyear_files.items():
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            continue

        rows: Iterable[Mapping[str, str]] = ()
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                with open(path, "r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f, delimiter=";", quotechar='"')
                    rows = list(reader)
                break
            except UnicodeDecodeError:
                continue
        else:
            # All encodings failed; skip this year.
            continue

        for row in rows:
            if not _is_vwo_row(row):
                continue

            vest = _brin_key_from_row(row)
            if not vest:
                continue

            naam = (row.get(COL_INSTELLINGSNAAM_VESTIGING) or "").strip().strip('"')
            gemeente = (row.get(COL_GEMEENTENAAM) or "").strip().strip('"')
            subj = (row.get(COL_VAK_AFKORTING) or "").strip().strip('"').upper()
            if not subj:
                # 对 profiel 计算来说，没有清晰的科目缩写就无法匹配，跳过。
                continue

            # 优先使用“计入文凭的统考平均分”，否则退回到总统考平均分。
            # DUO CSV 列名可能为 "GEM  CIJFER..." 或 "GEM. CIJFER..."
            cijfer = _parse_float_nl(row.get(COL_GEM_CE_MEETELLEND))
            if cijfer is None:
                cijfer = _parse_float_nl(row.get(COL_GEM_CE_MEETELLEND_ALT))
            if cijfer is None:
                cijfer = _parse_float_nl(row.get(COL_GEM_CE_TOTAAL))
            if cijfer is None:
                cijfer = _parse_float_nl(row.get(COL_GEM_CE_TOTAAL_ALT))
            if cijfer is None:
                continue

            if vest not in schools:
                schools[vest] = SchoolYearCentralExamScores(naam=naam, gemeente=gemeente)

            per_year = schools[vest].years.setdefault(year_label, {})
            # 若同一 school×year×subject 多次出现，后者覆盖前者即可（按 DUO 口径不应多次）。
            per_year[subj] = cijfer

    return schools


__all__ = [
    "SchoolYearScores",
    "SchoolYearCentralExamScores",
    "load_vwo_exam_cijferlijst_scores",
    "load_vwo_central_exam_scores",
]

