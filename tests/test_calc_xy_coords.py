"""单元测试：VO 中学 X/Y 计算逻辑（alleschools.loaders.vo_loader + compute）"""
import pytest
from alleschools.loaders import vo_loader


def _parse_int(s):
    return vo_loader._parse_int(s)


class TestParseInt:
    def test_empty_or_none_returns_2(self):
        assert _parse_int("") == 2
        assert _parse_int(None) == 2
        assert _parse_int("  ") == 2

    def test_less_than_5_returns_2(self):
        assert _parse_int("<5") == 2
        assert _parse_int('"<5"') == 2

    def test_valid_integers(self):
        assert _parse_int("0") == 0
        assert _parse_int("10") == 10
        assert _parse_int("  42  ") == 42
        assert _parse_int('"100"') == 100

    def test_invalid_returns_0(self):
        assert _parse_int("abc") == 0
        assert _parse_int("12.5") == 0


class TestIsHavoVwo:
    def test_havo_vwo_true(self):
        assert vo_loader.is_havo_vwo("HAVO") is True
        assert vo_loader.is_havo_vwo("VWO") is True
        assert vo_loader.is_havo_vwo(" havo ") is True
        assert vo_loader.is_havo_vwo('"VWO"') is True

    def test_other_false(self):
        assert vo_loader.is_havo_vwo("VMBO") is False
        assert vo_loader.is_havo_vwo("") is False
        assert vo_loader.is_havo_vwo(None) is False


class TestIsVmbo:
    def test_vmbo_true(self):
        assert vo_loader.is_vmbo("VMBO") is True
        assert vo_loader.is_vmbo(" vmbo ") is True

    def test_other_false(self):
        assert vo_loader.is_vmbo("HAVO") is False
        assert vo_loader.is_vmbo("VWO") is False
        assert vo_loader.is_vmbo("") is False


class TestIsScienceHavoVwo:
    def test_science_true(self):
        assert vo_loader.is_science_havo_vwo("N&T") is True
        assert vo_loader.is_science_havo_vwo("N&G") is True
        assert vo_loader.is_science_havo_vwo("N&T/N&G") is True
        assert vo_loader.is_science_havo_vwo("something N&T something") is True

    def test_non_science_false(self):
        assert vo_loader.is_science_havo_vwo("economie") is False
        assert vo_loader.is_science_havo_vwo("") is False
        assert vo_loader.is_science_havo_vwo(None) is False


class TestIsScienceVmbo:
    def test_techniek_true(self):
        assert vo_loader.is_science_vmbo("techniek") is True
        assert vo_loader.is_science_vmbo("Techniek") is True
        assert vo_loader.is_science_vmbo("vmbo techniek") is True

    def test_other_false(self):
        assert vo_loader.is_science_vmbo("economie") is False
        assert vo_loader.is_science_vmbo("") is False
