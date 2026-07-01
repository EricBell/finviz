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
    "cap_small",
    "ta_gap_u3"
  ],
  "rows": 5,
  "order": "-change",
  "table": "Overview",
  "request_method": "sequential",
  "sort_hint": [
    "gap",
    "volume",
    "liquidity"
  ]
}
```

## Result
Rows: 5

| Ticker | Company | Price | Change | Volume | Market Cap | Sector | Industry | Country |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SOC | Sable Offshore Corp | 4.28 | 38.80% | 73,543,746 | 659.90M | Energy | Oil & Gas Drilling | USA |
| RAAQ | Real Asset Acquisition Corp | 13.15 | 21.76% | 2,052,467 | 302.45M | Financial | Shell Companies | USA |
| DVLT | Datavault AI Inc | 0.40 | 15.05% | 97,477,468 | 344.51M | Technology | Software - Infrastructure | USA |
| AMPL | Amplitude Inc | 8.68 | 13.40% | 5,845,446 | 1.15B | Technology | Software - Application | USA |
| AIOT | PowerFleet Inc | 4.32 | 12.66% | 1,740,949 | 578.99M | Technology | Software - Infrastructure | USA |

Raw artifact: `screen.json`
