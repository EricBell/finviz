# Draft Output

## Objective
Finviz screen request

## Finviz Mode
screen

## Criteria
```json
{
  "filters": [
    "sh_price_u10",
    "sh_relvol_o2",
    "ta_sma50_pa"
  ],
  "rows": 7,
  "order": "-change",
  "table": "Overview",
  "request_method": "sequential",
  "sort_hint": [
    "gap",
    "relative volume",
    "price change",
    "liquidity"
  ]
}
```

## Result
Rows: 7

| Ticker | Company | Price | Change | Volume | Market Cap | Sector | Industry | Country |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LHAI | Linkhome Holdings Inc | 1.74 | 162.88% | 271,043,596 | 28.15M | Real Estate | Real Estate Services | USA |
| DXF | Eason Technology Ltd ADR | 0.85 | 133.34% | 205,779,919 | 1.34M | Financial | Credit Services | China |
| EHGO | Eshallgo Inc | 2.53 | 94.62% | 48,220,924 | 5.59M | Industrials | Business Equipment & Supplies | China |
| CANF | Can-Fite Biopharma Ltd ADR | 4.55 | 53.20% | 55,077,878 | 9.74M | Healthcare | Biotechnology | Israel |
| JEM | 707 Cayman Holdings Ltd | 5.65 | 42.32% | 56,316,047 | - | Consumer Cyclical | Apparel Retail | USA |
| STKE | Sol Strategies Inc | 1.65 | 41.03% | 3,858,035 | 58.76M | Financial | Capital Markets | Canada |
| ICU | SeaStar Medical Holding Corp | 4.74 | 29.16% | 383,250 | 18.95M | Healthcare | Biotechnology | USA |

Raw artifact: `screen.json`
