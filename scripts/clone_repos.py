#!/usr/bin/env python3
"""Clone the repositories selected by mine_github_repos.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path | None = None) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=str(cwd) if cwd else None, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-json", default="data/top_repos.json")
    parser.add_argument("--dest", default="data/repos")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="If a repo already exists, update it with git pull --ff-only.",
    )
    args = parser.parse_args()

    repos_doc = json.loads(Path(args.repos_json).read_text(encoding="utf-8"))
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    for repo in repos_doc["repositories"]:
        target = dest / repo["name"]
        if target.exists():
            if args.refresh:
                run(["git", "pull", "--ff-only"], cwd=target)
            else:
                print(f"Skipping existing repository: {target}")
            continue
        run(["git", "clone", "--depth", "1", repo["clone_url"], str(target)])

    return 0


if __name__ == "__main__":
    sys.exit(main())
