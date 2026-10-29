#!/usr/bin/env python3
import datetime as dt, json, os, urllib.parse, urllib.request
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
for repo in api("/users/" + login + "/repos", {"type":"owner","sort":"updated","per_page":100}):
    page = 1
    while page <= 10:
        commits = api("/repos/" + repo["full_name"] + "/commits", {"author":login,"since":since,"until":until,"per_page":100,"page":page})
        for commit in commits:
            day = commit.get("commit", {}).get("author", {}).get("date", "")[:10]
            if day in counts: counts[day] += 1
        if len(commits) < 100: break
        page += 1

width, height, left, right, top, bottom = 900, 430, 70, 30, 45, 70
chart_w, chart_h = width-left-right, height-top-bottom
scale = max(1, max(counts.values(), default=0))
bar_w = chart_w / 7 * 0.55
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" rx="18" fill="#ffffff"/>', '<text x="40" y="32" font-family="Arial" font-size="20" font-weight="700" fill="#111827">Commits — derniers 7 jours</text>']
for step in range(scale + 1):
    y = top + chart_h - step / scale * chart_h
    svg += [f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>', f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#6b7280">{step}</text>']
for i, day in enumerate(days):
    value = counts[day.isoformat()]
    center = left + (i + .5) * chart_w / 7
    bar_h = value / scale * chart_h
    x, y = center - bar_w / 2, top + chart_h - bar_h
    svg += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(2,bar_h):.1f}" rx="7" fill="#315cff"/>', f'<text x="{center:.1f}" y="{y-10:.1f}" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700" fill="#111827">{value}</text>', f'<text x="{center:.1f}" y="{height-32}" text-anchor="middle" font-family="Arial" font-size="12" fill="#6b7280">{escape(day.strftime("%a %d/%m"))}</text>']
svg += [f'<text x="{left}" y="{height-10}" font-family="Arial" font-size="11" fill="#9ca3af">Auteur : {escape(login)}</text>', "</svg>"]
Path("dist").mkdir(exist_ok=True)
Path("dist/commits-last-7-days.svg").write_text("\n".join(svg), encoding="utf-8")
print("Commit counts:", counts)
