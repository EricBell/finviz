# Intake Notes

## Request
Find low priced breakout stocks with relative volume above 2 and price above the 50 day moving average. Return the 7 strongest.

## Objective
Finviz screen request

## Workflow
```json
{
  "domain": "finviz",
  "mode": "screen",
  "criteria": {
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
}
```

## Constraints
- Use Finviz filters and return a concise result set.

## Assumptions
- Interpreted low-priced language as under $10.
- Interpreted relative volume > 2 as a Finviz relative volume filter.
- Interpreted 'above SMA50' as price above the moving average.
- Used price change as a proxy for 'strongest'.

## Open Questions
- none recorded

## Expected Output
A Finviz result set or lookup based on the inferred mode.
