# finviz-api — Overview

> Unofficial Python library for scraping stock data, screener results, insider transactions, analyst ratings, and news from finviz.com.

## Purpose

This is a scraping library (not an official API) that extracts financial market data from finviz.com. It targets traders, investors, and data analysts who need programmatic access to FinViz's stock screener, quote pages, news feeds, and insider trading tables. Data is delayed 15–20 minutes per FinViz's terms, so it is suited for research and analysis, not live trading.

v2.0.0 was a major rewrite to fix broken scraping after FinViz updated their DOM structure.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| HTML parsing | lxml + cssselect |
| HTTP (sync) | requests + tenacity (exponential retry) |
| HTTP (async) | aiohttp |
| Progress display | tqdm |
| Build | setuptools / pyproject.toml |
| Linting | ruff |
| Type checking | mypy |
| Tests | pytest + pytest-asyncio |

## Directory Structure

```
finviz/
├── finviz/                        # Main package
│   ├── __init__.py                # Public API surface (re-exports key functions)
│   ├── main_func.py               # get_stock(), get_news(), get_insider(), get_analyst_price_targets(), get_all_news()
│   ├── screener.py                # Screener class — multi-page stock screening
│   ├── portfolio.py               # Portfolio class — FinViz portfolio management (requires login)
│   ├── config.py                  # USER_AGENT string and connection settings
│   ├── filters.json               # Cached filter options (auto-generated from FinViz)
│   ├── helper_functions/
│   │   ├── request_functions.py   # http_request_get(), sequential_data_scrape(), Connector (async)
│   │   ├── scraper_functions.py   # get_table(), get_total_rows(), get_page_urls(), download_chart_image()
│   │   ├── save_data.py           # export_to_csv(), export_to_db() (SQLite)
│   │   ├── display_functions.py   # create_table_string() for pretty-printing
│   │   └── error_handling.py      # Custom exceptions: InvalidTableType, NoResults, ConnectionTimeout
│   └── tests/
│       ├── conftest.py
│       ├── test_stock.py
│       ├── test_screener.py
│       └── test_integration.py    # Real network tests (marked slow)
├── example.py                     # Usage examples
├── pyproject.toml
└── requirements.txt
```

## Architecture

**Request flow:** All HTTP goes through `http_request_get()` in `request_functions.py`. It uses `requests` synchronously with SSL verification disabled (FinViz uses self-signed/unusual certs — `urllib3` warnings are suppressed). For multi-page screener results, either `sequential_data_scrape()` (with `tenacity` exponential retry) or the `Connector` async class (using `aiohttp`) fetches all pages.

**Page caching:** `main_func.py` keeps a module-level `STOCK_PAGE` dict keyed by ticker. Multiple calls for the same ticker within a session reuse the cached parsed lxml tree. Pass `force_refresh=True` to `get_page()` to bypass.

**Screener pagination:** FinViz shows 20 rows per page. `get_page_urls()` calculates the number of pages from the total row count, builds URLs with `?r=1`, `?r=21`, etc., and either sequential or async scraping fetches them all.

**Filter caching:** `Screener.load_filter_dict()` fetches and parses available filters from FinViz's screener page and writes them to `finviz/filters.json`. Subsequent calls read from this cached file unless `reload=False` is passed.

**CSS selectors:** All scraping targets FinViz's current DOM — `tr.table-dark-row`, `td.snapshot-td2`, `table.styled-table-new`, `table.js-table-ratings`, etc. Fallback to old selectors is built in throughout for resilience to future DOM changes.

## Integrations

| External Service | Purpose | Where |
|-----------------|---------|-------|
| finviz.com/quote.ashx | Stock detail pages | `main_func.py` |
| finviz.com/screener.ashx | Screener results | `screener.py` |
| finviz.com/news.ashx | General market news | `main_func.py` |
| finviz.com/chart.ashx | Chart image downloads | `scraper_functions.py` |

No authentication is required for public data. The `Portfolio` class does require a FinViz account email and password.

## Database & Data Layer

No persistent database for core operations. Export options:
- **CSV**: `Screener.to_csv(filename)` via `export_to_csv()` in `save_data.py`
- **SQLite**: `Screener.to_sqlite(filename)` via `export_to_db()` in `save_data.py`
- **pandas DataFrame**: `Screener.to_dataframe()` — requires `pandas` as an optional dependency

## Connectivity & Configuration

| Setting | How to configure |
|---------|-----------------|
| `DISABLE_TQDM=1` | Env var — disables progress bars in sequential scraping |
| `USER_AGENT` | Hardcoded in `config.py` as Chrome 120 UA string |
| `CONCURRENT_CONNECTIONS` | `config.py` — default 30 (async mode) |
| `CONNECTION_TIMEOUT` | `config.py` — default 30000ms (async mode) |

All requests go to `https://finviz.com` with SSL verification disabled (`verify=False`).

## Key Entry Points

1. **`finviz/__init__.py`** — The public API: imports `get_stock`, `get_news`, `get_insider`, `get_analyst_price_targets`, `get_all_news`, `Portfolio`, `Screener`.
2. **`finviz/main_func.py`** — Individual stock functions; all share the `STOCK_PAGE` in-memory cache.
3. **`finviz/screener.py:Screener.__search_screener()`** — Core screener logic; handles both sync and async multi-page fetching.
4. **`finviz/helper_functions/request_functions.py`** — All HTTP transport logic lives here.

## Notes & Gotchas

- **SSL warnings suppressed globally**: `urllib3.disable_warnings()` is called at import time in `request_functions.py`.
- **`asyncio.SelectorEventLoop()` forced**: `Connector.run_connector()` explicitly sets a `SelectorEventLoop`, which may cause issues in environments that already have a running event loop (e.g., Jupyter notebooks).
- **`filters.json` is auto-generated**: If missing or stale, call `Screener.load_filter_dict(reload=False)` to regenerate from FinViz. The file is committed to the repo as a snapshot.
- **`__len__` returns total results, not `len(data)`**: `len(screener_instance)` returns the total row count from FinViz, not the number of locally fetched rows — can be surprising.
- **`Screener.__call__` accumulates filters**: Calling a `Screener` instance adds to existing tickers/filters rather than replacing them (except `table` and `order`, which are replaced).
- **Terms of Service**: Per the README, scraping FinViz may violate their ToS. The library includes a disclaimer.
- **`get_all_news()` uses old selectors**: Unlike `get_news()`, it still uses `td[class="nn-date"]` and `a[class="nn-tab-link"]` — potential fragility if FinViz updates this page.
