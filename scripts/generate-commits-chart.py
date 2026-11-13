#!/usr/bin/env python3
"""Generate a GitHub contribution chart for the latest 31 UTC dates."""

import datetime as dt
import json
import math
import os
import urllib.request
from pathlib import Path


NB_DAYS = 31
OUTPUT = Path("dist/commits-last-30-days.svg")
GRAPHQL_URL = "https://api.github.com/graphql"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def utc_date(now=None):
    """Return the date used by GitHub's UTC contribution calendar."""
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(dt.timezone.utc).date()


def build_days(today):
    """Build the inclusive UTC window: today and the previous 30 dates."""
    return [today - dt.timedelta(days=offset) for offset in range(NB_DAYS - 1, -1, -1)]


def extract_counts(payload, days):
    """Validate a GraphQL response and return counts for every requested date."""
    errors = payload.get("errors")
    user = payload.get("data", {}).get("user")
    if errors or not user:
        raise ValueError(f"Erreur GraphQL : {errors or 'utilisateur introuvable'}")

    try:
        weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    except (KeyError, TypeError) as error:
        raise ValueError("Réponse GraphQL invalide : calendrier absent") from error

    found = {
        item["date"]: item["contributionCount"]
        for week in weeks
        for item in week.get("contributionDays", [])
        if "date" in item and "contributionCount" in item
    }
    requested = [day.isoformat() for day in days]
    missing = [date for date in requested if date not in found]
    if missing:
        raise ValueError(f"Données incomplètes : {len(missing)} jour(s) absent(s)")

    return {date: found[date] for date in requested}


def fetch_counts(login, days, token):
    """Read the user's contribution calendar from GitHub GraphQL."""
    body = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": login,
                "from": f"{days[0].isoformat()}T00:00:00Z",
                "to": f"{days[-1].isoformat()}T23:59:59Z",
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Charlyken-contribution-graph",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return extract_counts(json.load(response), days)


def nice_step(max_value, max_ticks=5):
    """Choose a readable 1/2/5-based Y-axis step."""
    if max_value <= 0:
        return 1
    rough = max_value / max_ticks
    magnitude = 10 ** math.floor(math.log10(rough))
    normalized = rough / magnitude
    if normalized <= 1:
        factor = 1
    elif normalized <= 2:
        factor = 2
    elif normalized <= 5:
        factor = 5
    else:
        factor = 10
    return factor * magnitude


def smooth_path(points):
    path = f"M {points[0][0]:.1f},{points[0][1]:.1f}"
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        midpoint = (x0 + x1) / 2
        path += f" C {midpoint:.1f},{y0:.1f} {midpoint:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    return path


def build_svg(days, counts):
    """Render contribution counts using the actual UTC date for each point."""
    if not days:
        raise ValueError("La période du graphique ne peut pas être vide")

    width, height = 1500, 523
    left, right, top, bottom = 112, 60, 100, 86
    chart_width = width - left - right
    chart_height = height - top - bottom
    maximum = max(counts[day.isoformat()] for day in days)
    step = nice_step(maximum)
    y_max = max(step * 2, math.ceil(maximum / step) * step)
    x_step = chart_width / max(1, len(days) - 1)
    total = sum(counts[day.isoformat()] for day in days)

    def y_for(value):
        return top + chart_height - value / y_max * chart_height

    points = [
        (left + index * x_step, y_for(counts[day.isoformat()]))
        for index, day in enumerate(days)
    ]
    font = 'font-family="Arial, sans-serif" font-weight="700"'
    title = (
        f"Charlyken&#39;s Contributions: {days[0]:%d/%m} - {days[-1]:%d/%m} "
        f"({total} total)"
    )
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="1" y="1" width="1498" height="521" rx="2" fill="#0b0f14" stroke="#707781" stroke-width="2"/>',
        '<defs><filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
        f'<text x="750" y="50" text-anchor="middle" {font} font-size="22" fill="#4cc9f0">{title}</text>',
    ]

    value = 0
    while value <= y_max:
        y = y_for(value)
        svg.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#123847" stroke-width="2" stroke-dasharray="2 5"/>',
                f'<text x="{left - 14}" y="{y + 6:.1f}" text-anchor="end" {font} font-size="16" fill="#35b9df">{value:g}</text>',
            ]
        )
        value += step

    for index, day in enumerate(days):
        x = left + index * x_step
        svg.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + chart_height}" stroke="#123847" stroke-width="2" stroke-dasharray="2 5"/>'
        )
        show_label = len(days) <= 10 or (len(days) - 1 - index) % 3 == 0
        if show_label:
            svg.append(
                f'<text x="{x:.1f}" y="{top + chart_height + 26}" text-anchor="middle" {font} font-size="15" fill="#35b9df">{day:%d/%m}</text>'
            )

    svg.append(
        f'<path d="{smooth_path(points)}" fill="none" stroke="#55d6f5" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>'
    )
    for x, y in points:
        svg.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#f7f7f7" stroke="#ffffff" stroke-width="2"/>'
        )

    middle_y = top + chart_height / 2
    svg.extend(
        [
            f'<text x="38" y="{middle_y:.1f}" transform="rotate(-90 38 {middle_y:.1f})" text-anchor="middle" {font} font-size="16" fill="#35b9df">Contributions</text>',
            f'<text x="{left + chart_width / 2:.1f}" y="{height - 28}" text-anchor="middle" {font} font-size="16" fill="#35b9df">Date (UTC, dd/mm)</text>',
            "</svg>",
        ]
    )
    return "\n".join(svg)


def main():
    token = os.environ["GITHUB_TOKEN"]
    login = os.environ.get("GITHUB_LOGIN", "Charlyken")
    days = build_days(utc_date())
    counts = fetch_counts(login, days, token)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(build_svg(days, counts), encoding="utf-8")
    print("Contribution counts:", counts)


if __name__ == "__main__":
    main()
