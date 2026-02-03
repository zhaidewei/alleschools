"""单元测试：PO 端核心工具函数。"""

from alleschools.compute.indicators import get_woz_for_year
from alleschools.loaders.duo_loader import _parse_int as parse_int


class TestParseInt:
    def test_empty_or_less_5_returns_2(self):
        assert parse_int("") == 2
        assert parse_int(None) == 2  # type: ignore[arg-type]
        assert parse_int("<5") == 2

    def test_valid_integers(self):
        assert parse_int("0") == 0
        assert parse_int("10") == 10
        assert parse_int('"100"') == 100

    def test_invalid_returns_0(self):
        assert parse_int("abc") == 0


class TestGetWozForYear:
    def test_exact_year_exists(self):
        woz = {("1234", 2021): 250.0}
        assert get_woz_for_year(woz, [2020, 2021, 2022], "1234", 2021) == 250.0

    def test_fallback_to_nearest_year(self):
        woz = {("1234", 2020): 200.0, ("1234", 2022): 300.0}
        # 请求 2021，最近为 2020 或 2022（差 1），应返回其一
        result = get_woz_for_year(woz, [2020, 2022], "1234", 2021)
        assert result in (200.0, 300.0)

    def test_no_available_years_returns_none(self):
        woz = {}
        assert get_woz_for_year(woz, [], "1234", 2021) is None

    def test_pc4_not_in_woz_returns_none(self):
        woz = {("9999", 2021): 100.0}
        assert get_woz_for_year(woz, [2021], "1234", 2021) is None

    def test_prefer_closer_year(self):
        woz = {("1234", 2020): 200.0, ("1234", 2022): 300.0, ("1234", 2023): 310.0}
        # 请求 2021，最近应为 2020 或 2022（差 1），不应是 2023（差 2）
        result = get_woz_for_year(woz, [2020, 2022, 2023], "1234", 2021)
        assert result in (200.0, 300.0)
