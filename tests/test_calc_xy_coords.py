"""单元测试：calc_xy_coords（中学 X/Y 坐标计算）"""
import pytest
import calc_xy_coords as m


class TestParseInt:
    def test_empty_or_none_returns_2(self):
        assert m.parse_int("") == 2
        assert m.parse_int(None) == 2
        assert m.parse_int("  ") == 2

    def test_less_than_5_returns_2(self):
        assert m.parse_int("<5") == 2
        assert m.parse_int('"<5"') == 2

    def test_valid_integers(self):
        assert m.parse_int("0") == 0
        assert m.parse_int("10") == 10
        assert m.parse_int("  42  ") == 42
        assert m.parse_int('"100"') == 100

    def test_invalid_returns_0(self):
        assert m.parse_int("abc") == 0
        assert m.parse_int("12.5") == 0


class TestIsHavoVwo:
    def test_havo_vwo_true(self):
        assert m.is_havo_vwo("HAVO") is True
        assert m.is_havo_vwo("VWO") is True
        assert m.is_havo_vwo(" havo ") is True
        assert m.is_havo_vwo('"VWO"') is True

    def test_other_false(self):
        assert m.is_havo_vwo("VMBO") is False
        assert m.is_havo_vwo("") is False
        assert m.is_havo_vwo(None) is False


class TestIsVmbo:
    def test_vmbo_true(self):
        assert m.is_vmbo("VMBO") is True
        assert m.is_vmbo(" vmbo ") is True

    def test_other_false(self):
        assert m.is_vmbo("HAVO") is False
        assert m.is_vmbo("VWO") is False
        assert m.is_vmbo("") is False


class TestIsScienceHavoVwo:
    def test_science_true(self):
        assert m.is_science_havo_vwo("N&T") is True
        assert m.is_science_havo_vwo("N&G") is True
        assert m.is_science_havo_vwo("N&T/N&G") is True
        assert m.is_science_havo_vwo("something N&T something") is True

    def test_non_science_false(self):
        assert m.is_science_havo_vwo("economie") is False
        assert m.is_science_havo_vwo("") is False
        assert m.is_science_havo_vwo(None) is False


class TestIsScienceVmbo:
    def test_techniek_true(self):
        assert m.is_science_vmbo("techniek") is True
        assert m.is_science_vmbo("Techniek") is True
        assert m.is_science_vmbo("vmbo techniek") is True

    def test_other_false(self):
        assert m.is_science_vmbo("economie") is False
        assert m.is_science_vmbo("") is False
