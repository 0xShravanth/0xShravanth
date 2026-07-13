"""
Fetches all public repos for the configured GitHub user, keeps the ones that
have a "homepage" (i.e. a deployed/hosted link) set on GitHub, checks each
link's live status, and rewrites the HOSTED_PROJECTS block in README.md.

Run by .github/workflows/update-hosted-projects.yml on a schedule + on push.
"""

import os
import re
import sys
import requests

USERNAME = os.environ.get("GH_USERNAME", "0xShravanth")
README_PATH = os.environ.get("README_PATH", "README.md")
START_MARKER = "<!-- HOSTED_PROJECTS:START -->"
END_MARKER = "<!-- HOSTED_PROJECTS:END -->"

API_URL = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated"


def fetch_repos():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    repos = []
    page = 1
    while True:
        resp = requests.get(f"{API_URL}&page={page}", headers=headers, timeout=15)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def build_table(repos):
    hosted = [r for r in repos if r.get("homepage") and r["homepage"].strip()]
    hosted.sort(key=lambda r: r.get("pushed_at", ""), reverse=True)

    if not hosted:
        return "_No hosted projects detected yet — set a repo's \"Website\" field in GitHub repo settings to have it appear here._"

    rows = [
        "| Project | Live Link | Status | Description |",
        "|---|---|---|---|",
    ]
    for r in hosted:
        name = r["name"]
        url = r["homepage"].strip()
        repo_url = r["html_url"]
        desc = (r.get("description") or "").replace("|", "-")
        badge = f"![status](https://img.shields.io/website?url={requests.utils.quote(url, safe='')}&up_message=live&down_message=offline&style=flat-square)"
        rows.append(f"| [{name}]({repo_url}) | [{url}]({url}) | {badge} | {desc} |")

    return "\n".join(rows)


def update_readme(table):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )
    replacement = f"{START_MARKER}\n{table}\n{END_MARKER}"

    if pattern.search(content):
        new_content = pattern.sub(replacement, content)
    else:
        new_content = content.rstrip() + f"\n\n## 🚀 Hosted Projects\n\n{replacement}\n"

    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README updated.")
        return True

    print("No changes.")
    return False


def main():
    repos = fetch_repos()
    table = build_table(repos)
    changed = update_readme(table)
    # Exit code 0 always; workflow checks git diff to decide whether to commit
    sys.exit(0)


if __name__ == "__main__":
    main()