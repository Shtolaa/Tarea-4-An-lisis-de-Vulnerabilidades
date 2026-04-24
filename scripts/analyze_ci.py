#!/usr/bin/env python3
"""Inspect GitHub Actions workflows for risky CI/CD patterns."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


ACTION_REF_RE = re.compile(r"uses:\s*([^@\s]+)@([^\s#]+)", re.IGNORECASE)
HEX_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def inspect_workflow(path: Path, repo_name: str) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[dict] = []
    lines = text.splitlines()

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        lower = stripped.lower()

        if lower.startswith("pull_request_target:"):
            findings.append(
                finding(repo_name, path, number, "high", "pull_request_target", stripped)
            )
        if lower.startswith("permissions:") and "write-all" in lower:
            findings.append(
                finding(repo_name, path, number, "high", "permissions_write_all", stripped)
            )
        if re.search(r"\bsecrets:\s*inherit\b", lower):
            findings.append(
                finding(repo_name, path, number, "medium", "secrets_inherit", stripped)
            )
        if "curl " in lower and ("| sh" in lower or "| bash" in lower):
            findings.append(
                finding(repo_name, path, number, "high", "curl_pipe_shell", stripped)
            )

        match = ACTION_REF_RE.search(stripped)
        if match:
            action, ref = match.groups()
            if not HEX_SHA_RE.match(ref):
                findings.append(
                    finding(
                        repo_name,
                        path,
                        number,
                        "medium",
                        "unpinned_action",
                        f"{action}@{ref}",
                    )
                )

    if re.search(r"permissions:\s*\n\s+contents:\s*write", text, re.IGNORECASE):
        findings.append(
            finding(repo_name, path, 1, "medium", "contents_write_permission", "contents: write")
        )

    return findings


def finding(repo_name: str, path: Path, line: int, severity: str, rule: str, evidence: str) -> dict:
    return {
        "repo": repo_name,
        "workflow": str(path),
        "line": line,
        "severity": severity,
        "rule": rule,
        "evidence": evidence,
    }


def write_csv(path: Path, findings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["repo", "workflow", "line", "severity", "rule", "evidence"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(findings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-json", default="data/top_repos.json")
    parser.add_argument("--repos-dir", default="data/repos")
    parser.add_argument("--out-json", default="reports/ci/ci_findings.json")
    parser.add_argument("--out-csv", default="reports/ci/ci_findings.csv")
    args = parser.parse_args()

    repos_doc = json.loads(Path(args.repos_json).read_text(encoding="utf-8"))
    repos_dir = Path(args.repos_dir)
    findings: list[dict] = []

    for repo in repos_doc["repositories"]:
        name = repo["name"]
        workflow_dir = repos_dir / name / ".github" / "workflows"
        if not workflow_dir.exists():
            continue
        for workflow in sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml")):
            findings.extend(inspect_workflow(workflow, name))

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(Path(args.out_csv), findings)
    print(f"CI/CD findings: {len(findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
