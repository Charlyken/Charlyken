# Contribution Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate an accurate, date-labelled 31-day contribution graph that follows GitHub's UTC calendar and refreshes every six hours.

**Architecture:** The Python generator will expose deterministic date and SVG functions, while the network boundary reads `contributionCalendar` through GitHub GraphQL. Unit tests will exercise the rendered dates, UTC window, and invalid API responses without contacting GitHub.

**Tech Stack:** Python 3 standard library, `unittest`, GitHub GraphQL API, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-13-contribution-calendar-design.md`

## Global Constraints

- GitHub profile contributions are compared in UTC.
- Generate today plus the previous 30 days.
- Use only Python's standard library.
- Publish `dist/commits-last-30-days.svg` to the `commits-chart` branch.

## Review Focus

- Month boundaries: labels must use the actual day and month.
- UTC day boundaries: the final date must come from UTC, not the runner's local zone.
- Empty or incomplete GraphQL responses: generation must fail instead of publishing a misleading graph.
- A day with zero contributions: it must remain present in the series.
- Large daily counts: the Y-axis must scale without clipping.

---

### Task 1: Deterministic contribution graph

**Files:**
- Create: `tests/test_generate_commits_chart.py`
- Modify: `scripts/generate-commits-chart.py`

**Interfaces:**
- Produces: `build_days(today: date) -> list[date]`, `extract_counts(payload: dict, days: list[date]) -> dict[str, int]`, and `build_svg(days: list[date], counts: dict[str, int]) -> str`.

- [ ] Write failing tests for a UTC date window across a month boundary, real `dd/mm` labels, preserved zero-count days, scaling, and incomplete GraphQL data.
- [ ] Run `python -m unittest discover -s tests -v` and confirm the failures describe the missing interfaces and old numeric labels.
- [ ] Refactor the generator into the tested functions and replace HTML scraping with GraphQL `contributionCalendar`.
- [ ] Run `python -m unittest discover -s tests -v` and confirm all tests pass.
- [ ] Run the generator against GitHub with the existing token boundary and inspect the generated SVG.

### Task 2: Publishing and README integration

**Files:**
- Modify: `.github/workflows/generate-commits-chart.yml`
- Modify: `.github/workflows/generate-snake.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `dist/commits-last-30-days.svg` from Task 1.
- Produces: a six-hour scheduled workflow and a README image URL on the `commits-chart` branch.

- [ ] Update the chart workflow to run every six hours, use the repository owner dynamically, and prevent overlapping deployments.
- [ ] Update the README filename and accessible alt text; add dark-mode snake selection.
- [ ] Validate both workflow files as YAML and verify every README image URL responds successfully.

### Task 3: Final verification and delivery

**Files:**
- Review all changed files.

- [ ] Run the complete unit-test suite.
- [ ] Run a deterministic local generation using a fixed fixture and confirm that the SVG contains the expected UTC dates.
- [ ] Review the diff for secrets, unrelated changes, and stale references to `commits-last-7-days.svg`.
- [ ] Commit the branch, push it, create and merge a pull request, then manually run the updated workflow.
