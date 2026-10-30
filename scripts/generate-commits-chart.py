#!/usr/bin/env python3
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path

token = os.environ["GITHUB_TOKEN"]
login = os.environ.get("GITHUB_LOGIN", "Charlyken")
today = dt.date.today()
days = [today - dt.timedelta(days=i) for i in range(30, -1, -1)]
counts = {d.isoformat(): 0 for d in days}

def api(path, params):
    url = "https://api.github.com" + path + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Charlyken-contribution-graph",
    })
    with urllib.request.urlopen(request) as response:
        return json.load(response)

contributions_url = "https://github.com/users/" + login + "/contributions?" + urllib.parse.urlencode({
    "from": days[0].isoformat(),
    "to": today.isoformat(),
})
request = urllib.request.Request(
    contributions_url,
    headers={"User-Agent": "Charlyken-contribution-graph"},
)
with urllib.request.urlopen(request) as response:
    html = response.read().decode("utf-8")

pattern = re.compile(
    r'<td[^>]*data-date="([^"]+)"[^>]*>.*?<tool-tip[^>]*>(.*?)</tool-tip>',
    re.DOTALL,
)
for date, tooltip in pattern.findall(html):
    if date in counts:
        match = re.search(r"(\d+) contributions?", tooltip)
        counts[date] = int(match.group(1)) if match else 0

width, height = 1500, 523
left, right, top, bottom = 112, 60, 100, 86
chart_width = width - left - right
chart_height = height - top - bottom
max_value = max(counts.values(), default=0)
y_max = max(2, ((max_value + 1) // 2) * 2)
x_step = chart_width / 30
y_step = chart_height / y_max * 2
points = []

for index, day in enumerate(days):
    x = left + index * x_step
    y = top + chart_height - (counts[day.isoformat()] / y_max * chart_height)
    points.append((x, y))

def smooth_path(values):
    path = f"M {values[0][0]:.1f},{values[0][1]:.1f}"
    for index in range(1, len(values)):
        x0, y0 = values[index - 1]
        x1, y1 = values[index]
        mid = (x0 + x1) / 2
        path += f" C {mid:.1f},{y0:.1f} {mid:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    return path

path = smooth_path(points)
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<rect x="1" y="1" width="1498" height="521" rx="2" fill="#0b0f14" stroke="#707781" stroke-width="2"/>',
    '<defs><filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
    '<text x="750" y="50" text-anchor="middle" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#4cc9f0">Charlyken&#39;s Contribution Graph</text>',
]

for value in range(0, y_max + 1, 2):
    y = top + chart_height - (value / y_max * chart_height)
    svg += [
        f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#123847" stroke-width="2" stroke-dasharray="2 5"/>',
        f'<text x="{left-14}" y="{y+6:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#35b9df">{value}</text>',
    ]

for index in range(31):
    x = left + index * x_step
    svg.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top+chart_height}" stroke="#123847" stroke-width="2" stroke-dasharray="2 5"/>')
    svg.append(f'<text x="{x:.1f}" y="{top+chart_height+26}" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#35b9df">{index + 1}</text>')

svg += [
    f'<path d="{path}" fill="none" stroke="#55d6f5" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>',
]

for x, y in points:
    svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#f7f7f7" stroke="#ffffff" stroke-width="2"/>')

svg += [
    f'<text x="38" y="{top + chart_height / 2:.1f}" transform="rotate(-90 38 {top + chart_height / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#35b9df">Contributions</text>',
    f'<text x="{left + chart_width / 2:.1f}" y="{height-28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#35b9df">Days</text>',
    "</svg>",
]

Path("dist").mkdir(exist_ok=True)
Path("dist/commits-last-7-days.svg").write_text("\n".join(svg), encoding="utf-8")
print("Contribution counts:", counts)
