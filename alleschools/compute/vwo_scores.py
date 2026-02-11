from __future__ import annotations

"""
Computation helpers for VWO exam score based indicators.

First step for the "VO X axis = VWO average score" feature:

- Given per‑school, per‑year subject‑level cijferlijst scores
  (loaded via `load_vwo_exam_cijferlijst_scores`), compute:
  - per‑year medians; and
  - a simple "latest year" school‑level indicator suitable as an X axis.

The more advanced profiel‑specific indices described in the backlog
can be added on top of the same raw structure later.
"""

from dataclasses import dataclass
from typing import Dict, Mapping, MutableMapping, Optional, Sequence, Tuple

from alleschools.loaders.vwo_exam_loader import SchoolYearScores


@dataclass
class SchoolVwoMean:
    """Computed VWO average scores for a single school."""

    brin: str
    naam: str
    gemeente: str
    # year_label -> average cijferlijst for that year (or None if < min_subjects)
    yearly_mean: MutableMapping[str, Optional[float]]
    # chosen overall indicator for the school (e.g. latest year)
    indicator: Optional[float]


def _compute_yearly_means(
    scores: Mapping[str, Sequence[float]],
    min_subjects: int,
) -> Dict[str, Optional[float]]:
    """Helper: compute per‑year simple averages with an optional min‑subject threshold."""
    out: Dict[str, Optional[float]] = {}
    for year_label, vals in scores.items():
        vs = [float(v) for v in vals if v is not None]
        if len(vs) < min_subjects:
            out[year_label] = None
        else:
            out[year_label] = float(sum(vs) / len(vs))
    return out


def compute_vwo_mean_latest_year(
    schools: Mapping[str, SchoolYearScores],
    *,
    min_subjects_per_year: int = 3,
) -> Dict[str, SchoolVwoMean]:
    """
    Compute a simple "VWO average score per school" indicator.

    Strategy (documenting assumptions explicitly):

    - For each school + schoolyear we take the arithmetic mean of all
      subject‑level cijferlijst averages for that year.
    - Schoolyears with fewer than `min_subjects_per_year` distinct subjects
      are ignored (their mean is treated as missing).
    - The overall indicator is the average from the **latest** schoolyear
      (lexicographically largest year label) that has a valid mean.

    This follows your updated requirement of using the original averages
    (not a median) while still giving one VWO score per school.
    """
    results: Dict[str, SchoolVwoMean] = {}

    for brin, s in schools.items():
        yr_means = _compute_yearly_means(s.years, min_subjects_per_year)
        # Pick latest year with a valid mean
        chosen: Optional[Tuple[str, float]] = None
        for year_label in sorted(yr_means.keys()):
            val = yr_means[year_label]
            if val is None:
                continue
            # Sorted ascending; we keep the last valid one as "latest"
            chosen = (year_label, float(val))

        indicator = chosen[1] if chosen is not None else None

        results[brin] = SchoolVwoMean(
            brin=brin,
            naam=s.naam,
            gemeente=s.gemeente,
            yearly_mean=yr_means,
            indicator=indicator,
        )

    return results


__all__ = [
    "SchoolVwoMean",
    "compute_vwo_mean_latest_year",
]

