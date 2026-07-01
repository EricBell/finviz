# Finviz Tools Implementation Handoff

## Goal
Make the Finviz ICM workflow robust across the broad Finviz screener catalog by using:
1. **LLM-based interpretation** of user requests
2. **A generic semantic DSL** for criteria
3. **A catalog-driven compiler** that maps DSL fields to Finviz filters
4. **Deterministic validation/execution**

The current approach works for common cases, but it still needs hand-tuned phrase handling for every new screener concept. This plan replaces that with a scalable design.

---

## Current State

### Already in place
- `finviz-tools/` ICM-style workflow folders
- `run_stage.py`
- `01_intake/stage.py` with LLM-first request interpretation
- `03_execute/stage.py` executing `shared.finviz` helpers
- `shared/llm.py`
- `shared/finviz/compile.py`
- `shared/finviz/filters.py`
- `shared/finviz/screener.py`
- `shared/finviz/stock.py`
- `CONFIG.md` for LLM env vars

### Problems remaining
- `01_intake` still contains fallback phrase rules
- `shared/finviz/compile.py` still hardcodes many special cases
- screener breadth is not fully covered
- adding new screener concepts requires code edits too often

---

## Target Design

### Data flow
`request.md` -> LLM -> semantic DSL -> compiler -> Finviz filters -> screener/lookup -> review

### Key principle
**The LLM should express intent, not Finviz tags.**

The compiler should translate a generic DSL into actual Finviz filters using the screener catalog.

---

## Proposed DSL

Use a structured schema like:

```json
{
  "domain": "finviz",
  "tool": "finviz.screen",
  "mode": "screen",
  "criteria": {
    "sector": "Energy",
    "industry": "Airlines",
    "exchange": "NASDAQ",
    "index": "S&P 500",
    "market_cap": {"class": "large"},
    "price": {"min": 2, "max": 10},
    "performance": {
      "change_from_open_gte": 3,
      "gap_up_gte": 2,
      "change_gte": 5
    },
    "liquidity": {
      "relative_volume_gte": 2,
      "average_volume_gte": 500000
    },
    "technical": {
      "sma": {"period": 50, "relation": "above"}
    },
    "limit": 5,
    "ranking": {
      "primary": "change_from_open",
      "direction": "desc"
    }
  }
}
```

This DSL should be the stable contract between intake and execution.

---

## Implementation Plan

### Phase 1: Clean up intake and make it DSL-first

#### File: `finviz-tools/01_intake/stage.py`
- Keep LLM-first behavior.
- Update the system prompt so it **always emits the DSL**, not raw Finviz tags.
- Remove or minimize fallback phrase-specific logic.
- If fallback is needed, keep it limited to broad request classification only.
- Support price ranges explicitly:
  - `<$10 and >$2`
  - `between $2 and $10`
  - `$2-$10`
- Preserve all detected constraints in the DSL.
- Ensure all LLM output is coerced/validated into the schema.

#### Validation to add
- `workflow.domain` must be `finviz` or `generic`
- if `tool == finviz.screen`, `criteria` must be present
- `price.min` and `price.max` may coexist
- `limit` must be an integer when present

---

### Phase 2: Build a catalog-driven compiler

#### File: `finviz-tools/shared/finviz/compile.py`
Replace one-off phrase mapping with catalog-aware compilation.

#### Compiler responsibilities
- Load `finviz/filters.json`
- Resolve generic DSL fields to Finviz filter tags
- Support multiple filter forms for the same concept
- Produce a **list of filter tags** for screener queries

#### Concepts to support generically
- sector
- industry
- exchange
- index
- market_cap class
- price range
- gap up/down
- change from open
- change %
- relative volume
- average volume
- SMA relations
- 52-week high/low style concepts later
- dividend yield / P/E / valuation fields later

#### Strategy
1. Build a small field-to-filter resolver layer.
2. Keep exact-match catalog lookup for categories like sector/exchange/index.
3. Support numeric thresholds by choosing the nearest available Finviz label.
4. For ranges, emit both bounds when possible.
5. For unsupported concepts, raise `FinvizInvalidFilterError` rather than silently dropping them.

#### Important compiler additions
- price range -> `Over $X` + `Under $Y`
- change from open >= N -> `Change from Open` -> `Up N%`
- gap >= N -> `Gap` -> `Up N%`
- relative volume >= N -> `Relative Volume` -> nearest `Over N` label
- average volume >= N -> `Average Volume` -> nearest `Over ...` label
- SMA relation -> correct moving average group

---

### Phase 3: Make catalog resolution reusable

#### New helper module suggestion
Create or expand a helper like:
- `finviz-tools/shared/finviz/catalog.py`

#### Responsibilities
- load filter groups from `filters.json`
- normalize group names
- normalize labels
- find closest label for thresholds
- provide utilities like:
  - `resolve_group(name)`
  - `resolve_label(group, label)`
  - `nearest_numeric_label(group, value, direction)`

This avoids scattered logic inside the compiler.

---

### Phase 4: Improve execution-stage behavior

#### File: `finviz-tools/03_execute/stage.py`
- Keep routing by `tool` / `mode`.
- Ensure the execute stage consumes only the DSL and not raw phrase assumptions.
- Add support for an empty result path:
  - if no rows, write empty `final.md` in review.
- Optionally add a `rank_rows()` helper if ranking is requested.
- Make sure row count / output formatting remain stable.

#### Optional improvement
- If the DSL includes `sort` or `ranking`, apply post-query ranking in Python rather than relying on Finviz order alone.

---

### Phase 5: Make review/output handling explicit

#### File: `finviz-tools/04_review/stage.py`
- If no results, write an empty `final.md`.
- Otherwise wrap the draft in a clear final output.
- Include a short note when the output is empty.

---

## Recommended File Changes

### Must edit
- `finviz-tools/01_intake/stage.py`
- `finviz-tools/shared/finviz/compile.py`
- `finviz-tools/shared/finviz/filters.py`
- `finviz-tools/shared/finviz/__init__.py`
- `finviz-tools/03_execute/stage.py`
- `finviz-tools/04_review/stage.py`

### Likely add
- `finviz-tools/shared/finviz/catalog.py`
- `finviz-tools/shared/finviz/schema.py` or `types.py`
- `finviz-tools/shared/finviz/validate.py`

---

## LLM Prompt Guidance

The intake prompt should explicitly tell the model:
- emit structured JSON only
- prefer DSL fields over tag strings
- preserve all constraints
- if a range is specified, keep both bounds
- use Finviz tool names only at the top level

Suggested rule wording:
> Convert user requests into semantic screening criteria. Do not output Finviz filter tags unless the schema explicitly allows raw filters. Preserve range constraints, category constraints, and ranking hints.

---

## Testing Plan

### Add/verify test cases
1. `top 5 large cap energy stocks up at least 3% since the open`
2. `price <$10 and >$2`
3. `small cap stocks gapping up`
4. `low priced breakout stocks with relative volume above 2 and price above the 50 day moving average`
5. `find airline stocks under $20 with average volume over 500K`
6. `top 5 energy stocks` should not include non-energy names

### Expected checks
- intake JSON preserves all constraints
- compiler emits both price bounds when asked
- screener results obey sector constraints
- no silent dropping of DSL fields
- empty-result path writes empty `final.md`

---

## Acceptance Criteria

The implementation is done when:
- the LLM emits a stable semantic DSL
- the compiler maps DSL -> Finviz filters across the screener catalog
- new Finviz concepts do not require one-off prompt rules for every phrase
- price ranges and other multi-bound constraints are preserved
- execution works via `uv run run_stage.py ...`
- empty-result requests produce empty final output when requested

---

## Execution Order for Claude Code

1. Update intake prompt/schema
2. Add/expand catalog helpers
3. Refactor compiler to use catalog helpers
4. Simplify/remove brittle fallback phrase rules
5. Update execute/review behavior
6. Run `uv run` tests against the sample requests
7. Inspect generated `task.json` and `draft.md`

---

## Notes

- Keep `uv` as the only supported execution style.
- Prefer small deterministic helpers around a large semantic DSL.
- Don’t keep adding phrase-specific rules unless they are truly necessary.
- The catalog should be the source of breadth; the LLM should be the source of interpretation.
