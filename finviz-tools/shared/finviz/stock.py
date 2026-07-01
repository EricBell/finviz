"""Thin wrappers over the bundled Finviz stock helpers."""

from __future__ import annotations

def get_stock(ticker: str):
    from finviz.main_func import get_stock as _get_stock

    return _get_stock(ticker)


def get_news(ticker: str):
    from finviz.main_func import get_news as _get_news

    return _get_news(ticker)


def get_insider(ticker: str):
    from finviz.main_func import get_insider as _get_insider

    return _get_insider(ticker)


def get_analyst_targets(ticker: str, last_ratings: int = 10):
    from finviz.main_func import get_analyst_price_targets as _get_analyst_price_targets

    return _get_analyst_price_targets(ticker, last_ratings=last_ratings)


def get_all_news():
    from finviz.main_func import get_all_news as _get_all_news

    return _get_all_news()
