from __future__ import annotations

import html
import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

API = "https://api.github.com"
USERNAME = os.environ.get("GITHUB_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ASSETS = Path("assets")
ASSETS.mkdir(parents=True, exist_ok=True)

if not USERNAME:
    raise SystemExit("GITHUB_USERNAME or GITHUB_REPOSITORY_OWNER is required")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "github-profile-card-generator",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def get_json(url: str):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def get_public_repos() -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"type": "owner", "sort": "updated", "per_page": 100, "page": page}
        )
        batch = get_json(f"{API}/users/{urllib.parse.quote(USERNAME)}/repos?{query}")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [repo for repo in repos if not repo.get("fork")]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def stats_svg(theme: str, stats: dict) -> str:
    dark = theme == "dark"
    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    title = "#58a6ff" if dark else "#0969da"
    text = "#f0f6fc" if dark else "#1f2328"
    muted = "#8b949e" if dark else "#656d76"
    accent = "#7c3aed"

    values = [
        ("Public repositories", stats["repos"]),
        ("Stars earned", stats["stars"]),
        ("Followers", stats["followers"]),
        ("Forks", stats["forks"]),
    ]

    cells = []
    positions = [(24, 88), (218, 88), (24, 142), (218, 142)]
    for (label, value), (x, y) in zip(values, positions):
        cells.append(
            f'<text x="{x}" y="{y - 19}" fill="{muted}" font-size="12">{esc(label)}</text>'
            f'<text x="{x}" y="{y}" fill="{text}" font-size="22" font-weight="700">{esc(value)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="170" viewBox="0 0 420 170" role="img" aria-label="GitHub profile statistics">
  <rect x="0.5" y="0.5" width="419" height="169" rx="12" fill="{bg}" stroke="{border}"/>
  <circle cx="24" cy="28" r="5" fill="{accent}"/>
  <text x="38" y="34" fill="{title}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="18" font-weight="700">GitHub Overview</text>
  <text x="24" y="52" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="11">{esc(USERNAME)} · generated from GitHub API</text>
  <g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">{''.join(cells)}</g>
</svg>'''


LANG_COLORS = {
    "Java": "#b07219",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "PHP": "#4F5D95",
    "C#": "#178600",
    "Dart": "#00B4AB",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "Shell": "#89e051",
    "C++": "#f34b7d",
    "C": "#555555",
    "Kotlin": "#A97BFF",
}
DEFAULT_COLORS = ["#58a6ff", "#7c3aed", "#2ea043", "#f0883e", "#db61a2"]


def languages_svg(theme: str, languages: dict[str, int]) -> str:
    dark = theme == "dark"
    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    title = "#58a6ff" if dark else "#0969da"
    text = "#f0f6fc" if dark else "#1f2328"
    muted = "#8b949e" if dark else "#656d76"

    ranked = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:5]
    total = sum(value for _, value in ranked) or 1

    if not ranked:
        rows = f'<text x="24" y="96" fill="{muted}" font-size="13">No public language data yet.</text>'
        bar = ""
    else:
        rows_list = []
        x = 24.0
        bar_segments = []
        for index, (name, value) in enumerate(ranked):
            pct = value / total * 100
            color = LANG_COLORS.get(name, DEFAULT_COLORS[index % len(DEFAULT_COLORS)])
            width = 372 * value / total
            bar_segments.append(
                f'<rect x="{x:.2f}" y="58" width="{max(width, 1):.2f}" height="8" fill="{color}"/>'
            )
            x += width
            row_y = 88 + index * 15
            rows_list.append(
                f'<circle cx="28" cy="{row_y - 4}" r="4" fill="{color}"/>'
                f'<text x="39" y="{row_y}" fill="{text}" font-size="12" font-weight="600">{esc(name)}</text>'
                f'<text x="390" y="{row_y}" fill="{muted}" font-size="12" text-anchor="end">{pct:.1f}%</text>'
            )
        rows = "".join(rows_list)
        bar = f'<clipPath id="bar"><rect x="24" y="58" width="372" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">{"".join(bar_segments)}</g>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="170" viewBox="0 0 420 170" role="img" aria-label="Top repository languages">
  <rect x="0.5" y="0.5" width="419" height="169" rx="12" fill="{bg}" stroke="{border}"/>
  <text x="24" y="34" fill="{title}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="18" font-weight="700">Repository Languages</text>
  <text x="24" y="50" fill="{muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="11">Aggregated across public, non-fork repositories</text>
  {bar}
  <g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">{rows}</g>
</svg>'''


def main() -> None:
    profile = get_json(f"{API}/users/{urllib.parse.quote(USERNAME)}")
    repos = get_public_repos()

    stats = {
        "repos": len(repos),
        "stars": sum(repo.get("stargazers_count", 0) for repo in repos),
        "followers": profile.get("followers", 0),
        "forks": sum(repo.get("forks_count", 0) for repo in repos),
    }

    language_totals: dict[str, int] = defaultdict(int)
    for repo in repos:
        languages_url = repo.get("languages_url")
        if not languages_url:
            continue
        try:
            repo_languages = get_json(languages_url)
        except Exception as exc:
            print(f"warning: could not read languages for {repo.get('name')}: {exc}")
            continue
        for language, byte_count in repo_languages.items():
            language_totals[language] += int(byte_count)

    for theme in ("light", "dark"):
        (ASSETS / f"profile-stats-{theme}.svg").write_text(
            stats_svg(theme, stats), encoding="utf-8"
        )
        (ASSETS / f"top-languages-{theme}.svg").write_text(
            languages_svg(theme, dict(language_totals)), encoding="utf-8"
        )

    print(f"Generated profile cards for {USERNAME}")


if __name__ == "__main__":
    main()
