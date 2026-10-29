#!/usr/bin/env python3
import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path

token = os.environ["GITHUB_TOKEN"]
login = os.environ.get("GITHUB_LOGIN", "Charlyken")
today = dt.date.today()
days = [today - dt.timedelta(days=i) for i in range(6, -1, -1)]
counts = {d.isoformat(): 0 for d in days}

def api(path, params):
    url = "https://api.github.com" + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Charlyken-commit-chart",
    })
    with urllib.request.urlopen(req) as response:
        return json.load(response)

since = dt.datetime.combine(days[0], dt.time.min, tzinfo=dt.timezone.utc).isoformat()
until = dt.datetime.combine(today + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc).isoformat()
query = f"author:{login} committer-date:{days[0].isoformat()}..{today.isoformat()}"
for page in range(1, 11):
    result = api("/search/commits", {"q": query, "sort": "committer-date", "order": "asc", "per_page": 100, "page": page})
    commits = result.get("items", [])
    for item in commits:
        date = item.get("commit", {}).get("author", {}).get("date", "")[:10]
        if date in counts:
            counts[date] += 1
    if len(commits) < 100:
        break

width, height, left, right, top, bottom = 960, 460, 70, 35, 55, 75
chart_w, chart_h = width - left - right, height - top - bottom
max_value = max(counts.values(), default=0)
scale = max(1, max_value)
step_x = chart_w / 6
points = []
for i, day in enumerate(days):
    x = left + i * step_x
    y = top + chart_h - (counts[day.isoformat()] / scale * chart_h)
    points.append((x, y))

line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
area = f"{left},{top+chart_h} " + line + f" {left+chart_w},{top+chart_h}"
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#315cff" stop-opacity=".35"/><stop offset="100%" stop-color="#315cff" stop-opacity=".02"/></linearGradient><filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="5" stdDeviation="6" flood-color="#315cff" flood-opacity=".18"/></filter></defs>',
    '<rect width="100%" height="100%" rx="22" fill="#f8faff"/>',
    '<text x="40" y="34" font-family="Arial, sans-serif" font-size="21" font-weight="700" fill="#111827">Commit activity</text>',
    '<text x="40" y="54" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">Evolution des commits sur les 7 derniers jours</text>',
]
for step in range(scale + 1):
    y = top + chart_h - step / scale * chart_h
    svg += [
        f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#dfe6f3" stroke-dasharray="4 6"/>',
        f'<text x="{left-14}" y="{y+4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#7b879d">{step}</text>',
    ]
svg.append(f'<polygon points="{area}" fill="url(#area)"/>')
svg.append(f'<polyline points="{line}" fill="none" stroke="#315cff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" filter="url(#shadow)"/>')
for i, day in enumerate(days):
    x, y = points[i]
    value = counts[day.isoformat()]
    svg += [
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#ffffff" stroke="#315cff" stroke-width="4"/>',
        f'<text x="{x:.1f}" y="{y-15:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#111827">{value}</text>',
        f'<text x="{x:.1f}" y="{height-35}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">{escape(day.strftime("%a %d/%m"))}</text>',
    ]
svg += [
    f'<text x="{left}" y="{height-12}" font-family="Arial, sans-serif" font-size="11" fill="#9ca3af">Auteur : {escape(login)} · commits publics trouvés via GitHub Search</text>',
    "</svg>",
]
Path("dist").mkdir(exist_ok=True)
Path("dist/commits-last-7-days.svg").write_text("\n".join(svg), encoding="utf-8")
print("Commit counts:", counts)
