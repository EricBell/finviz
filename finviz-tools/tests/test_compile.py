import pytest

from shared.finviz.compile import compile_semantic_filters
from shared.finviz.errors import FinvizInvalidFilterError


def _as_set(filters):
    return set(filters)


@pytest.mark.parametrize(
    "criteria,expected",
    [
        # 1. top 5 large cap energy stocks up at least 3% since the open
        (
            {
                "sector": "Energy",
                "market_cap": {"class": "large"},
                "performance": {"change_from_open_gte": 3},
            },
            {"sec_energy", "cap_large", "ta_changeopen_u3"},
        ),
        # 2. price <$10 and >$2
        (
            {"price": {"min": 2, "max": 10}},
            {"sh_price_o2", "sh_price_u10"},
        ),
        # 3. small cap stocks gapping up
        (
            {"market_cap": {"class": "small"}, "performance": {"gap_up_gte": 3}},
            {"cap_small", "ta_gap_u3"},
        ),
        # 4. low priced breakout stocks: rvol above 2, price above 50-day SMA
        (
            {
                "price": {"relation": "under", "value": 10},
                "liquidity": {"relative_volume_gte": 2},
                "technical": {"sma": {"period": 50, "relation": "above"}},
            },
            {"sh_price_u10", "sh_relvol_o2", "ta_sma50_pa"},
        ),
        # 5. airline stocks under $20 with average volume over 500K
        (
            {
                "industry": "Airlines",
                "price": {"max": 20},
                "liquidity": {"average_volume_gte": 500_000},
            },
            {"ind_airlines", "sh_price_u20", "sh_avgvol_o500"},
        ),
    ],
)
def test_compile_semantic_filters_sample_requests(criteria, expected):
    assert _as_set(compile_semantic_filters(criteria)) == expected


def test_compile_preserves_direct_filters():
    assert compile_semantic_filters({"filters": ["sec_energy"]}) == ["sec_energy"]


def test_compile_deduplicates_while_preserving_order():
    criteria = {"filters": ["sec_energy"], "sector": "Energy"}
    assert compile_semantic_filters(criteria) == ["sec_energy"]


def test_compile_unknown_sector_raises_not_silently_dropped():
    with pytest.raises(FinvizInvalidFilterError):
        compile_semantic_filters({"sector": "NotARealSector"})
