from alleschools.compute.vwo_profiles import compute_vwo_profile_indices_by_year
from alleschools.loaders.vwo_exam_loader import (
    SchoolYearCentralExamScores,
    _brin_key_from_row,
)


def test_yearly_profile_indices_keep_years_separate() -> None:
    schools = {
        "00AA00": SchoolYearCentralExamScores(
            naam="Testschool",
            gemeente="Utrecht",
            years={
                "2022-2023": {"WISB": 6.0, "NAT": 7.0, "SCHK": 8.0},
                "2023-2024": {"WISB": 8.0, "NAT": 7.0, "SCHK": 6.0},
            },
        )
    }

    result = compute_vwo_profile_indices_by_year(schools)

    assert result["00AA00"]["2022-2023"]["NT"] == 6.75
    assert result["00AA00"]["2023-2024"]["NT"] == 7.25


def test_profile_loader_normalizes_one_digit_branch_suffix() -> None:
    row = {"INSTELLINGSCODE": "02TE", "VESTIGINGSCODE": "0"}

    assert _brin_key_from_row(row) == "02TE00"
