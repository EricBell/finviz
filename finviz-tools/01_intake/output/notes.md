# Intake Notes

## Request
Find top 5 large cap energy stocks that are up at least 3% since the open.

## Objective
Finviz screen request

## Workflow
```json
{
  "domain": "finviz",
  "tool": "finviz.screen",
  "mode": "screen",
  "criteria": {
    "sector": "Energy",
    "market_cap": {
      "class": "large"
    },
    "performance": {
      "change_from_open_gte": 3
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
- Interpreted 'large cap' as a large-cap Finviz screen.

## Open Questions
- none recorded

## Expected Output
A Finviz result set or lookup based on the inferred mode.
