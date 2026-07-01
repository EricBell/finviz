# Intake Notes

## Request
Find top 5 large cap energy stocks that are up at least 3% since the open.

## Objective
Finviz screen request

## Workflow
```json
{
  "domain": "finviz",
  "mode": "screen",
  "criteria": {
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
}
```

## Constraints
- Use Finviz filters and return a concise result set.

## Assumptions
- Interpreted 'large cap' as Finviz cap_large.

## Open Questions
- none recorded

## Expected Output
A Finviz result set or lookup based on the inferred mode.
