# Beta Phase 1 Readiness Checklist

Complete this checklist before beginning live Beta Phase 1 usage.

## Required

- [ ] Full `pytest -q` suite is green.
- [ ] Database backup has been created.
- [ ] `v2.2.0-rc` tag exists.
- [ ] Application starts cleanly.
- [ ] Full market workflow completes end-to-end.
- [ ] Incremental price refresh completes without blocking issues.
- [ ] Indicator calculation completes successfully.
- [ ] Support detection completes successfully.
- [ ] Bounce validation completes successfully.
- [ ] Screening completes successfully.
- [ ] Candidate Detail opens for the top 20 candidates.
- [ ] Candidate Detail shows no raw placeholder strings.
- [ ] No UI blocking is observed during normal review.
- [ ] Logs have been reviewed after a full workflow run.
- [ ] Known deferred issues are documented.

## Data And Workflow

- [ ] Universe source is correct for beta usage.
- [ ] Cached OHLCV data is current enough for review.
- [ ] Technical indicators have been refreshed.
- [ ] Support levels have been refreshed.
- [ ] Bounce validations have been refreshed.
- [ ] Screening results are available.
- [ ] Top candidates can be exported or manually recorded.

## Candidate Detail Review

- [ ] Overview fields are readable.
- [ ] Technical tab is populated where data exists.
- [ ] Bounce History tab is populated where data exists.
- [ ] Fundamentals display clear missing-data labels when unavailable.
- [ ] Risk tab displays clear missing-data labels when unavailable.
- [ ] Institutional tab displays provider status without fake data.

## Beta Operating Rules

- [ ] No analytics changes during beta.
- [ ] No scoring changes during beta.
- [ ] No pipeline orchestration changes during beta.
- [ ] No threading changes during beta.
- [ ] No database architecture changes during beta.
- [ ] Feature requests are logged, not implemented.

## Sign-Off

- Reviewer:
- Date:
- Notes:

