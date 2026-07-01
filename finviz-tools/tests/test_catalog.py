import pytest

from shared.finviz.catalog import nearest_numeric_label, resolve_group, resolve_label
from shared.finviz.errors import FinvizInvalidFilterError


def test_resolve_group_exact_and_fuzzy():
    canonical, options = resolve_group("Sector")
    assert canonical == "Sector"
    assert "Energy" in options

    canonical, _ = resolve_group("market cap")
    assert canonical == "Market Cap."


def test_resolve_group_unknown_raises():
    with pytest.raises(FinvizInvalidFilterError):
        resolve_group("Not A Real Group")


def test_resolve_label_exact():
    assert resolve_label("Sector", "Energy") == "sec_energy"
    assert resolve_label("Market Cap.", "Large ($10bln to $200bln)") == "cap_large"


def test_resolve_label_unknown_raises():
    with pytest.raises(FinvizInvalidFilterError):
        resolve_label("Sector", "NotARealSector")


@pytest.mark.parametrize(
    "group,value,direction,expected",
    [
        # exact matches
        ("Relative Volume", 2, "over", "sh_relvol_o2"),
        ("Average Volume", 500_000, "over", "sh_avgvol_o500"),
        ("Price $", 2, "over", "sh_price_o2"),
        ("Price $", 10, "under", "sh_price_u10"),
        ("Gap", 3, "over", "ta_gap_u3"),
        # between-label thresholds: "over" must not undershoot, "under" must not overshoot
        ("Relative Volume", 2.2, "over", "sh_relvol_o3"),
        ("Average Volume", 600_000, "over", "sh_avgvol_o750"),
        ("Price $", 12, "under", "sh_price_u10"),
        ("Gap", 12, "over", "ta_gap_u15"),
        # out of range: fall back to the closest available label
        ("Relative Volume", 0.1, "over", "sh_relvol_o0.25"),
        ("Gap", 100, "over", "ta_gap_u20"),
    ],
)
def test_nearest_numeric_label(group, value, direction, expected):
    assert nearest_numeric_label(group, value, direction) == expected


def test_nearest_numeric_label_no_labels_for_direction_raises():
    with pytest.raises(FinvizInvalidFilterError):
        nearest_numeric_label("Sector", 1, "over")
