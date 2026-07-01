"""Thin wrappers over the bundled Finviz Screener class."""

from __future__ import annotations

from .filters import build_screener_kwargs


def run_screener(**kwargs) -> list[dict]:
    """Run a screener query and return the parsed rows."""

    from finviz.screener import Screener

    screener = Screener(**kwargs)
    return list(screener.data)


def screen(criteria: dict) -> list[dict]:
    """Run a screener query from a higher-level criteria dictionary."""

    return run_screener(**build_screener_kwargs(criteria))


def screener_from_url(url: str, rows: int | None = None) -> list[dict]:
    """Initialize a screener from a Finviz screener URL and return rows."""

    from finviz.screener import Screener

    return list(Screener.init_from_url(url, rows=rows).data)
