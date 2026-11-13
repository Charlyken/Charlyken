# Contribution Calendar Design

## Intent

Make the custom profile graph match GitHub's contribution calendar: real UTC dates on the horizontal axis, GitHub contribution counts for those dates, and refreshes throughout the day.

## Goals

- Read daily contribution counts from GitHub's GraphQL `contributionCalendar` instead of scraping HTML.
- Display the actual `dd/mm` dates for the trailing 31-day window.
- Use UTC because GitHub timestamps profile contributions in UTC.
- Refresh every six hours and support manual runs.
- Keep the generated SVG available from the existing `commits-chart` branch.

## Non-goals

- Produce a commit-only graph; this graph intentionally mirrors GitHub contributions, which can include qualifying commits, pull requests, issues, and reviews.
- Change the contribution snake workflow beyond making its scheduled publishing safer.

## Approach

Use the existing Python generator with a small functional boundary: fetch GitHub data separately from SVG rendering. GraphQL provides `date` and `contributionCount`, while deterministic unit tests supply fixed counts and dates without network access. The workflow publishes `commits-last-30-days.svg` every six hours.

## Constraints

- Python standard library only.
- No network calls in tests.
- Fail rather than publish an incomplete or empty response.
- Preserve the current profile README layout.
