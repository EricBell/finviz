# Intake Notes

## Request
I want a screen of small cap stocks that are gapping up. Return the 5 strongest tickers.

## Objective
Finviz screen request

## Workflow
```json
{
  "domain": "finviz",
  "mode": "screen",
  "criteria": {
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
}
```

## Constraints
- Use Finviz filters and return a concise result set.

## Assumptions
- Interpreted 'small cap' as Finviz cap_small.
- Interpreted 'gapping up' as a 3%+ gap filter.
- Used price change as a proxy for 'strongest'.

## Open Questions
- none recorded

## Expected Output
A Finviz result set or lookup based on the inferred mode.
