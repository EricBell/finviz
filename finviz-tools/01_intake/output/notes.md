# Intake Notes

## Request
Find top 5 small cap  stocks that are up at least 3% since the open, less than $10 and more than $2. If there are none, create an empty final.md file.

## Objective
Finviz screen request

## Workflow
```json
{
  "domain": "finviz",
  "tool": "finviz.screen",
  "mode": "screen",
  "criteria": {
    "market_cap": {
      "class": "small"
    },
    "performance": {
      "change_from_open_gte": 3
    },
    "price": {
      "max": 10.0,
      "min": 2.0
    },
    "limit": 5,
    "ranking": {
      "primary": "change_from_open",
      "direction": "desc"
    }
  }
}
```

## Constraints
- Use the selected Finviz tool and return a concise result set.

## Assumptions
- none recorded

## Open Questions
- none recorded

## Expected Output
A Finviz result set or lookup based on the inferred mode.
