#!/usr/bin/env python3
"""Génère dist/commits-last-30-days.svg : contributions GitHub par jour sur 31 jours.

Source de données : API GraphQL (contributionsCollection), pas de scraping HTML.
Le script échoue (code != 0) si les données sont vides ou incohérentes, pour ne
jamais publier un graphe plat par erreur.
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

TOKEN = os.environ["GITHUB_TOKEN"]
LOGIN = os.environ.get("GITHUB_LOGIN", "Charlyken")
TZ = ZoneInfo(os.environ.get("CHART_TZ", "Europe/Paris"))
NB_DAYS = 31  # aujourd'hui + 30 jours précédents
OUTPUT = Path("dist/commits-last-30-days.svg")

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_counts(days):
    """Retourne {date_iso: nombre de contributions} pour chaque jour demandé."""
    payload = json.dumps({
        "query": QUERY,
        "variables": {
            "login": LOGIN,
            "from": f"{days[0].isoformat()}T00:00:00Z",
            "to": f"{days[-1].isoformat()}T23:59:59Z",
        },
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "Charlyken-contribution-graph",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)

    if data.get("errors") or not data.get("data", {}).get("user"):
        sys.exit(f"Erreur GraphQL : {data.get('errors') or 'utilisateur introuvable'}")

    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    found = {
        day["date"]: day["contributionCount"]
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    }
    wanted = {d.isoformat() for d in days}
    missing = wanted - found.keys()
    if missing:
        sys.exit(f"Données incomplètes : {len(missing)} jour(s) absent(s) de la réponse.")
    return {iso: found[iso] for iso in sorted(wanted)}


def nice_step(max_value, max_ticks=5):
    """Plus petit pas « rond » (1, 2, 5, 10, 20, 50...) donnant au plus max_ticks graduations."""
    step = 1
    while math.ceil(max_value / step) > max_ticks:
        magnitude = 10 ** int(math.log10(step))
        step = next(m * magnitude for m in (2, 5, 10) if m * magnitude > step)
    return step


def smooth_path(values):
    path = f"M {values[0][0]:.1f},{values[0][1]:.1f}"
    for (x0, y0), (x1, y1) in zip(values, values[1:]):
        mid = (x0 + x1) / 2
        path += f" C {mid:.1f},{y0:.1f} {mid:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    return path


def build_svg(days, counts):
    width, height = 1500, 523
    left, right, top, bottom = 112, 60, 100, 86
    chart_width = width - left - right
    chart_height = height - top - bottom

    max_value = max(counts.values())
    step = nice_step(max_value)
    y_max = max(math.ceil(max_value / step) * step, step * 2)
    x_step = chart_width / (NB_DAYS - 1)
    total = sum(counts.values())

    def y_of(value):
        return top + chart_height - value / y_max * chart_height

    points = [(left + i * x_step, y_of(counts[d.isoformat()])) for i, d in enumerate(days)]
    font = 'font-family="Arial, sans-serif" font-weight="700"'
    title = (
        f"Charlyken&#39;s Contributions : {days[0]:%d/%m} → {days[-1]:%d/%m} "
        f"({total} au total)"
    )

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="1" y="1" width="1498" height="521" rx="2" fill="#0b0f14" stroke="#707781" stroke-width="2"/>',
        '<defs><filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
        f'<text x="750" y="50" text-anchor="middle" {font} font-size="22" fill="#4cc9f0">{title}</text>',
    ]

    for value in range(0, y_max + 1, step):
        y = y_of(value)
        svg += [
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#123847" stroke-width="2" stroke-dasharray="2 5"/>',
            f'<text x="{left - 14}" y="{y + 6:.1f}" text-anchor="end" {font} font-size="16" fill="#35b9df">{value}</text>',
        ]

    for i, day in enumerate(days):
        x = left + i * x_step
        svg.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + chart_height}" stroke="#123847" stroke-width="2" stroke-dasharray="2 5"/>')
        if (NB_DAYS - 1 - i) % 3 == 0:  # une date sur trois, la dernière (aujourd'hui) toujours affichée
            svg.append(f'<text x="{x:.1f}" y="{top + chart_height + 26}" text-anchor="middle" {font} font-size="15" fill="#35b9df">{day:%d/%m}</text>')

    svg.append(f'<path d="{smooth_path(points)}" fill="none" stroke="#55d6f5" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>')
    for x, y in points:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#f7f7f7" stroke="#ffffff" stroke-width="2"/>')

    mid_y = top + chart_height / 2
    svg += [
        f'<text x="38" y="{mid_y:.1f}" transform="rotate(-90 38 {mid_y:.1f})" text-anchor="middle" {font} font-size="16" fill="#35b9df">Contributions</text>',
        f'<text x="{left + chart_width / 2:.1f}" y="{height - 28}" text-anchor="middle" {font} font-size="16" fill="#35b9df">Date (jj/mm)</text>',
        "</svg>",
    ]
    return "\n".join(svg)


def main():
    today = dt.datetime.now(TZ).date()
    days = [today - dt.timedelta(days=i) for i in range(NB_DAYS - 1, -1, -1)]
    counts = fetch_counts(days)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(build_svg(days, counts), encoding="utf-8")
    print("Contribution counts:", counts)


if __name__ == "__main__":
    main()
