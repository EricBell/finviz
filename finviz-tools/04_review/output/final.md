# Final Output

# Draft Output

## Objective
Finviz screen request

## Finviz Mode
screen

## Criteria
```json
{
  "filters": [
    "cap_large"
  ],
  "rows": 5,
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
Rows: 5

| Ticker | Company | Price | Change | Volume | Market Cap | Sector | Industry | Country |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Agilent Technologies Inc | 134.26 | 1.08% | 895,196 | 37.92B | Healthcare | Diagnostics & Research | USA |
| AA | Alcoa Corp | 46.85 | -10.14% | 12,434,569 | 12.36B | Basic Materials | Aluminum | USA |
| AAL | American Airlines Group Inc | 18.24 | 0.91% | 140,146,334 | 12.06B | Industrials | Airlines | USA |
| AAOI | Applied Optoelectronics Inc | 137.00 | -7.53% | 4,364,908 | 10.99B | Technology | Communication Equipment | USA |
| ABEV | Ambev SA ADR | 3.11 | -0.96% | 14,608,723 | 48.51B | Consumer Defensive | Beverages - Brewers | Brazil |

Raw artifact: `screen.json`
