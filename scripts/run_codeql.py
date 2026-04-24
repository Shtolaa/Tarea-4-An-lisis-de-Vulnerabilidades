#!/usr/bin/env python3
"""Run CodeQL against the selected repositories and emit SARIF reports."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


LANGUAGE_BY_EXTENSION = {
    ".js": "javascript-typescript",
    ".jsx": "javascript-typescript",
    ".ts": "javascript-typescript",
    ".tsx": "javascript-typescript",
    ".py": "python",
    ".go": "go",
    ".java": "java-kotlin",
    ".kt": "java-kotlin",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".rb": "ruby",
}


def detect_languages(repo_dir: Path) -> list[str]:
    found: set[str] = set()
    ignored = {".git", "node_modules", "dist", "build", ".next", "coverage"}
    for path in repo_dir.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        if language:
            found.add(language)
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-json", default="data/top_repos.json")
    parser.add_argument("--repos-dir", default="data/repos")
    parser.add_argument("--db-dir", default="reports/codeql/databases")
    parser.add_argument("--out-dir", default="reports/codeql")
    parser.add_argument(
        "--queries",
        default="",
        help=(
            "Optional CodeQL query or suite. If omitted, CodeQL uses its default "
            "queries for the database language."
        ),
    )
    args = parser.parse_args()

    if not shutil.which("codeql"):
        raise SystemExit("codeql is required. Install the CodeQL CLI before scanning.")

    repos_doc = json.loads(Path(args.repos_json).read_text(encoding="utf-8"))
    repos_dir = Path(args.repos_dir)
    db_dir = Path(args.db_dir)
    out_dir = Path(args.out_dir)
    db_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    for repo in repos_doc["repositories"]:
        name = repo["name"]
        source = repos_dir / name
        if not source.exists():
            print(f"Missing clone for {name}: {source}", file=sys.stderr)
            continue

        languages = detect_languages(source)
        if not languages:
            print(f"No CodeQL-supported languages detected for {name}")
            continue

        for language in languages:
            database = db_dir / f"{name}-{language}"
            sarif = out_dir / f"{name}-{language}.sarif"
            if not database.exists():
                create_command = [
                    "codeql",
                    "database",
                    "create",
                    str(database),
                    f"--language={language}",
                    f"--source-root={source}",
                    "--overwrite",
                ]
                print("+ " + " ".join(str(part) for part in create_command))
                subprocess.run(create_command, check=True)

            analyze_command = [
                "codeql",
                "database",
                "analyze",
                str(database),
                "--format=sarif-latest",
                f"--output={sarif}",
            ]
            if args.queries:
                analyze_command.insert(4, args.queries)
            print("+ " + " ".join(str(part) for part in analyze_command))
            subprocess.run(analyze_command, check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
