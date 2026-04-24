#!/usr/bin/env python3
"""Mine the most starred repositories from a GitHub organization.

The task requires GitHub API usage. This script calls the REST API directly,
sorts public repositories by stargazers, and stores a reproducible selection.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API_ROOT = "https://api.github.com"


def github_get(url: str) -> tuple[object, dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "flowise-vulnerability-course-miner",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            response_headers = {k.lower(): v for k, v in response.headers.items()}
            return payload, response_headers
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            raise RuntimeError(
                "GitHub API returned 401 Unauthorized. The GITHUB_TOKEN environment "
                "variable is set, but GitHub rejected it. Revoke leaked tokens, create "
                "a new one, or unset GITHUB_TOKEN to use unauthenticated public API access."
            ) from exc
        raise RuntimeError(f"GitHub API error {exc.code} for {url}: {detail}") from exc


def fetch_org_repos(org: str) -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"type": "public", "per_page": 100, "page": page}
        )
        url = f"{API_ROOT}/orgs/{urllib.parse.quote(org)}/repos?{query}"
        payload, headers = github_get(url)
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected GitHub payload for {url}: {payload!r}")
        repos.extend(payload)

        link_header = headers.get("link", "")
        if 'rel="next"' not in link_header:
            break
        page += 1

        remaining = headers.get("x-ratelimit-remaining")
        if remaining == "0":
            reset = int(headers.get("x-ratelimit-reset", "0"))
            sleep_for = max(reset - int(time.time()), 0) + 1
            time.sleep(sleep_for)

    return repos


def normalize_repo(repo: dict) -> dict:
    return {
        "id": repo.get("id"),
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "html_url": repo.get("html_url"),
        "clone_url": repo.get("clone_url"),
        "default_branch": repo.get("default_branch"),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "stargazers_count": repo.get("stargazers_count", 0),
        "forks_count": repo.get("forks_count", 0),
        "open_issues_count": repo.get("open_issues_count", 0),
        "archived": repo.get("archived", False),
        "disabled": repo.get("disabled", False),
        "pushed_at": repo.get("pushed_at"),
        "updated_at": repo.get("updated_at"),
        "created_at": repo.get("created_at"),
        "license": (repo.get("license") or {}).get("spdx_id"),
        "topics": repo.get("topics", []),
    }


def write_csv(path: Path, repos: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "full_name",
        "html_url",
        "clone_url",
        "default_branch",
        "language",
        "stargazers_count",
        "forks_count",
        "open_issues_count",
        "archived",
        "pushed_at",
        "license",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, repo in enumerate(repos, start=1):
            row = {field: repo.get(field) for field in fieldnames if field != "rank"}
            row["rank"] = index
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", default="FlowiseAI", help="GitHub organization")
    parser.add_argument("--top", type=int, default=5, help="Number of repositories")
    parser.add_argument("--out-json", default="data/top_repos.json")
    parser.add_argument("--out-csv", default="data/top_repos.csv")
    args = parser.parse_args()

    repos = fetch_org_repos(args.org)
    filtered = [repo for repo in repos if not repo.get("fork")]
    ranked = sorted(
        filtered,
        key=lambda repo: (
            int(repo.get("stargazers_count") or 0),
            int(repo.get("forks_count") or 0),
            repo.get("updated_at") or "",
        ),
        reverse=True,
    )[: args.top]
    normalized = [normalize_repo(repo) for repo in ranked]

    document = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "organization": args.org,
        "selection_criteria": (
            "Top public, non-fork repositories in the organization, sorted by "
            "stargazers_count descending using the GitHub REST API."
        ),
        "api_endpoint": f"{API_ROOT}/orgs/{args.org}/repos",
        "count": len(normalized),
        "repositories": normalized,
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(Path(args.out_csv), normalized)

    for index, repo in enumerate(normalized, start=1):
        print(f"{index}. {repo['full_name']} - {repo['stargazers_count']} stars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
