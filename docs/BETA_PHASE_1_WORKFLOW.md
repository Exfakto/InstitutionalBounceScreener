# Beta Phase 1 Workflow

Beta Phase 1 is a live-usage and feedback period. Feature development is frozen. The goal is to run the platform consistently, observe real-world behavior, and collect enough evidence to decide what belongs in Version 3.

## Daily Usage Routine

Use this routine on market days or whenever fresh candidate review is needed.

1. Confirm the application starts cleanly.
2. Update the universe only when needed.
3. Run an incremental price refresh.
4. Calculate indicators.
5. Detect support.
6. Validate bounces.
7. Run screening.
8. Review the top 20 candidates.
9. Open Candidate Detail for each reviewed candidate.
10. Record observations in the beta feedback log and signal tracking template.

Avoid changing settings mid-session unless the change is part of a deliberate beta note.

## Weekly Review Routine

At the end of each week:

1. Review all beta session notes for repeated issues.
2. Review the signal tracking template for early 5-day and 10-day outcomes.
3. Group bugs by severity and reproducibility.
4. Identify missing information that repeatedly affected candidate review.
5. Identify UI friction that slowed review.
6. Review logs for recurring warnings or errors.
7. Decide whether any issue blocks continued beta use.
8. Add only confirmed V3 candidates to the future work list.

## Full Market Workflow

Run the full market workflow when preparing a fresh beta baseline or when cached data may be stale.

Recommended order:

1. Update universe if the tracked universe has changed.
2. Refresh historical prices incrementally.
3. Calculate technical indicators.
4. Detect support levels.
5. Validate historical bounces.
6. Run screening.
7. Review top candidates.
8. Capture notes and signal tracking rows.

Do not use the beta phase to change pipeline orchestration, threading, scoring, or database architecture.

## Reviewing Top Candidates

For each top candidate:

1. Confirm company identity, exchange, sector, and industry are populated.
2. Review current price, latest close date, latest volume, and 52-week range.
3. Review technical indicators and support distance.
4. Review bounce history and validation strength.
5. Review fundamental and risk summaries where data exists.
6. Confirm institutional fields show provider status without fabricated data.
7. Record whether the candidate is actionable, watchlist-worthy, or rejected.

Focus on repeatability: record why a candidate looked useful or not useful, not just whether it ranked highly.

## What To Record Manually

Record:

- date and approximate time of review
- market condition
- workflow steps completed
- candidate count
- top candidates reviewed
- notable score/risk mismatches
- candidate detail gaps
- confusing labels
- slow operations
- errors, warnings, or crashes
- trade ideas worth tracking
- follow-up actions

## Issues To Log

Log any issue that affects confidence in the platform:

- incorrect or stale candidate data
- raw placeholder text
- missing Candidate Detail sections
- pipeline failures
- database errors
- long-running operations that appear frozen
- inconsistent scores between views
- candidate rows that cannot be opened
- confusing or misleading research text
- unexpected provider status messages

Include reproduction steps whenever possible.

## What Not To Change During Beta

Do not change:

- analytics formulas
- scoring weights
- screening rules
- pipeline orchestration
- threading behavior
- database architecture
- UI layout or redesign
- provider behavior beyond configuration required for testing

During Beta Phase 1, observations should become notes, not immediate feature work.

## Exit Criteria

Beta Phase 1 can exit when:

- the full test suite remains green
- the full market workflow completes reliably
- top 20 Candidate Detail review is repeatable
- no release-blocking placeholder strings are visible
- no recurring workflow crash is present
- known deferred issues are documented
- at least one full weekly review has been completed
- signal tracking has enough entries to evaluate early outcomes
- Version 3 candidates are separated from beta blockers
