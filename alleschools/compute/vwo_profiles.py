from __future__ import annotations

"""
Compute VO VWO profiel indices (NT / NG / EM / CM) based on central exam averages.

This module implements section 3.5 of VO_X_AXIS_VWO_MEDIAN_SCORE.md:

- For each school (vestiging) and schoolyear, we derive subject-level
  central exam averages C(vak) from DUO "examenkandidaten vwo en examencijfers".
- For each profiel (NT/NG/EM/CM) we combine the relevant subjects with
  fixed weights to get X_{profiel, jaar}.
- Across the most recent 5 schoolyears we apply a time weighting
  (w_0..w_4) to obtain X_{profiel}^{(5j)}.

The output is four mappings: profile_id -> { brin -> X_profile_5yr }.
"""

from typing import Dict, Mapping, MutableMapping, Sequence

from alleschools.loaders.vwo_exam_loader import SchoolYearCentralExamScores


# Canonical subject codes (based on AFKORTING VAKNAAM, uppercased)
SUBJ_WISB = "WISB"
SUBJ_WISA = "WISA"
SUBJ_WISC = "WISC"
SUBJ_NAT = "NAT"
SUBJ_SCHK = "SCHK"
SUBJ_BIOL = "BIOL"
SUBJ_ECON = "ECON"
SUBJ_BECO = "BECO"
SUBJ_GES = "GES"
SUBJ_EN = "ENTL"
SUBJ_DE = "DUTL"
SUBJ_FR = "FATL"
# DUO 部分学校使用「taal」版（无 literatuur）：ENZL/DUZL/FAZL，CM 计算时作为 fallback
SUBJ_EN_ALT = "ENZL"
SUBJ_DE_ALT = "DUZL"
SUBJ_FR_ALT = "FAZL"


ProfileId = str  # e.g. "NT", "NG", "EM", "CM"


def _get(subjects: Mapping[str, float], code: str) -> float | None:
    """Safe lookup in a subject-score mapping."""
    val = subjects.get(code)
    if val is None:
        return None
    return float(val)


def _compute_x_nt(subj: Mapping[str, float]) -> float | None:
    """NT: 0.5 * Wiskunde B + 0.25 * Natuurkunde + 0.25 * Scheikunde."""
    c_wisb = _get(subj, SUBJ_WISB)
    c_nat = _get(subj, SUBJ_NAT)
    c_schk = _get(subj, SUBJ_SCHK)
    if c_wisb is None or c_nat is None or c_schk is None:
        return None
    return 0.50 * c_wisb + 0.25 * c_nat + 0.25 * c_schk


def _compute_x_ng(subj: Mapping[str, float]) -> float | None:
    """NG: 0.35 * Biologie + 0.25 * Scheikunde + 0.40 * Wiskunde B."""
    c_biol = _get(subj, SUBJ_BIOL)
    c_schk = _get(subj, SUBJ_SCHK)
    c_wisb = _get(subj, SUBJ_WISB)
    if c_biol is None or c_schk is None or c_wisb is None:
        return None
    return 0.35 * c_biol + 0.25 * c_schk + 0.40 * c_wisb


def _compute_x_em(subj: Mapping[str, float]) -> float | None:
    """
    EM:
        X_EM = (1/3) * C(Economie) + (1/3) * C(Geschiedenis) + (1/3) * C_WIS^EM
    where:
        C_WIS^EM = avg(C(Wiskunde A), C(Wiskunde B)) if both exist;
        if only one of A/B exists, use that one;
        if both missing, no EM point.
    """
    c_econ = _get(subj, SUBJ_ECON)
    c_ges = _get(subj, SUBJ_GES)
    if c_econ is None or c_ges is None:
        return None

    c_wisa = _get(subj, SUBJ_WISA)
    c_wisb = _get(subj, SUBJ_WISB)
    if c_wisa is not None and c_wisb is not None:
        c_wis = 0.5 * (c_wisa + c_wisb)
    elif c_wisa is not None:
        c_wis = c_wisa
    elif c_wisb is not None:
        c_wis = c_wisb
    else:
        return None

    return (1.0 / 3.0) * (c_econ + c_ges + c_wis)


def _compute_x_cm(subj: Mapping[str, float]) -> float | None:
    """
    CM:
        X_CM = 0.333 * C(Geschiedenis) + 0.333 * C_WIS^CM + 0.333 * C_TALEN
    where:
        C_WIS^CM = avg(C(Wiskunde C), C(Wiskunde A)) if both exist;
        if only one of C/A exists, use that one;
        otherwise no CM point.
        C_TALEN = avg(Engels, Duits, Frans) over available ones;
        if none of the languages are present, no CM point.
    """
    c_ges = _get(subj, SUBJ_GES)
    if c_ges is None:
        return None

    c_wisc = _get(subj, SUBJ_WISC)
    c_wisa = _get(subj, SUBJ_WISA)
    if c_wisc is not None and c_wisa is not None:
        c_wis = 0.5 * (c_wisc + c_wisa)
    elif c_wisc is not None:
        c_wis = c_wisc
    elif c_wisa is not None:
        c_wis = c_wisa
    else:
        return None

    def _get_lang(subj: Mapping[str, float], prim: str, alt: str) -> float | None:
        v = _get(subj, prim)
        if v is not None:
            return v
        return _get(subj, alt)

    langs = []
    for prim, alt in ((SUBJ_EN, SUBJ_EN_ALT), (SUBJ_DE, SUBJ_DE_ALT), (SUBJ_FR, SUBJ_FR_ALT)):
        v = _get_lang(subj, prim, alt)
        if v is not None:
            langs.append(v)
    if not langs:
        return None
    c_talen = sum(langs) / len(langs)

    return 0.333 * c_ges + 0.333 * c_wis + 0.333 * c_talen


def compute_vwo_profile_indices(
    schools: Mapping[str, SchoolYearCentralExamScores],
    *,
    year_order: Sequence[str],
    year_weights: Mapping[str, float],
) -> Dict[ProfileId, Dict[str, float]]:
    """
    Compute 5-year weighted profiel indices X_NT, X_NG, X_EM, X_CM for each school.

    Parameters
    ----------
    schools:
        Mapping brin -> SchoolYearCentralExamScores, as returned by
        load_vwo_central_exam_scores.
    year_order:
        Ordered list of schoolyear labels (e.g. ["2020-2021", ..., "2024-2025"]).
        This is used only for determinism; actual weights come from year_weights.
    year_weights:
        Mapping year_label -> weight w_k. Missing years are treated as weight 0.

    Returns
    -------
    dict
        {
          "NT": { brin -> X_NT_5yr },
          "NG": { brin -> X_NG_5yr },
          "EM": { brin -> X_EM_5yr },
          "CM": { brin -> X_CM_5yr },
        }
    """
    profiles: Dict[ProfileId, Dict[str, float]] = {
        "NT": {},
        "NG": {},
        "EM": {},
        "CM": {},
    }

    for brin, school in schools.items():
        # Pre-compute per-year profile X for this school.
        per_year_profile: Dict[str, Dict[ProfileId, float]] = {}
        for year_label, subj_scores in school.years.items():
            x_nt = _compute_x_nt(subj_scores)
            x_ng = _compute_x_ng(subj_scores)
            x_em = _compute_x_em(subj_scores)
            x_cm = _compute_x_cm(subj_scores)

            if all(v is None for v in (x_nt, x_ng, x_em, x_cm)):
                continue
            per_year_profile[year_label] = {}
            if x_nt is not None:
                per_year_profile[year_label]["NT"] = float(x_nt)
            if x_ng is not None:
                per_year_profile[year_label]["NG"] = float(x_ng)
            if x_em is not None:
                per_year_profile[year_label]["EM"] = float(x_em)
            if x_cm is not None:
                per_year_profile[year_label]["CM"] = float(x_cm)

        if not per_year_profile:
            continue

        # Time-weighted aggregation for each profile separately.
        for prof in ("NT", "NG", "EM", "CM"):
            num = 0.0
            den = 0.0
            for year_label in year_order:
                year_vals = per_year_profile.get(year_label)
                if not year_vals or prof not in year_vals:
                    continue
                w = float(year_weights.get(year_label, 0.0) or 0.0)
                if w <= 0.0:
                    continue
                num += w * year_vals[prof]
                den += w
            if den <= 0.0:
                continue
            profiles[prof][brin] = num / den

    return profiles


__all__ = ["compute_vwo_profile_indices"]

