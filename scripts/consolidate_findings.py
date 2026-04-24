#!/usr/bin/env python3
"""Build course datasets from Grype, CodeQL and CI/CD outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def grype_rows(repo_name: str, path: Path) -> list[dict]:
    report = load_json(path, {"matches": []})
    rows: list[dict] = []
    for match in report.get("matches", []):
        vulnerability = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        rows.append(
            {
                "repo": repo_name,
                "scanner": "grype",
                "dimension": "dependencies",
                "rule_id": vulnerability.get("id"),
                "severity": vulnerability.get("severity"),
                "package_name": artifact.get("name"),
                "package_version": artifact.get("version"),
                "package_type": artifact.get("type"),
                "fixed_versions": ";".join(vulnerability.get("fix", {}).get("versions", [])),
                "description": vulnerability.get("description"),
                "source_file": "",
                "line": "",
            }
        )
    return rows


def codeql_rows(repo_name: str, sarif_path: Path) -> list[dict]:
    sarif = load_json(sarif_path, {"runs": []})
    rows: list[dict] = []
    for run in sarif.get("runs", []):
        rules = {}
        for tool_rule in run.get("tool", {}).get("driver", {}).get("rules", []):
            rules[tool_rule.get("id")] = tool_rule
        for result in run.get("results", []):
            rule_id = result.get("ruleId")
            rule = rules.get(rule_id, {})
            location = (result.get("locations") or [{}])[0].get("physicalLocation", {})
            region = location.get("region", {})
            rows.append(
                {
                    "repo": repo_name,
                    "scanner": "codeql",
                    "dimension": "source",
                    "rule_id": rule_id,
                    "severity": (
                        result.get("level")
                        or rule.get("properties", {}).get("security-severity")
                        or rule.get("defaultConfiguration", {}).get("level")
                    ),
                    "package_name": "",
                    "package_version": "",
                    "package_type": "",
                    "fixed_versions": "",
                    "description": result.get("message", {}).get("text"),
                    "source_file": location.get("artifactLocation", {}).get("uri", ""),
                    "line": region.get("startLine", ""),
                }
            )
    return rows


def ci_rows(ci_path: Path) -> list[dict]:
    findings = load_json(ci_path, [])
    rows: list[dict] = []
    for item in findings:
        rows.append(
            {
                "repo": item.get("repo"),
                "scanner": "workflow-inspector",
                "dimension": "ci_cd",
                "rule_id": item.get("rule"),
                "severity": item.get("severity"),
                "package_name": "",
                "package_version": "",
                "package_type": "",
                "fixed_versions": "",
                "description": item.get("evidence"),
                "source_file": item.get("workflow"),
                "line": item.get("line"),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "repo",
        "scanner",
        "dimension",
        "rule_id",
        "severity",
        "package_name",
        "package_version",
        "package_type",
        "fixed_versions",
        "description",
        "source_file",
        "line",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-json", default="data/top_repos.json")
    parser.add_argument("--grype-dir", default="reports/grype")
    parser.add_argument("--codeql-dir", default="reports/codeql")
    parser.add_argument("--ci-json", default="reports/ci/ci_findings.json")
    parser.add_argument("--out-csv", default="data/findings.csv")
    parser.add_argument("--summary-json", default="data/summary.json")
    args = parser.parse_args()

    repos_doc = load_json(Path(args.repos_json), {"repositories": []})
    rows: list[dict] = []
    for repo in repos_doc["repositories"]:
        name = repo["name"]
        rows.extend(grype_rows(name, Path(args.grype_dir) / f"{name}.grype.json"))
        for sarif_path in sorted(Path(args.codeql_dir).glob(f"{name}-*.sarif")):
            rows.extend(codeql_rows(name, sarif_path))
    rows.extend(ci_rows(Path(args.ci_json)))

    write_csv(Path(args.out_csv), rows)

    summary = {
        "total_findings": len(rows),
        "by_repo": Counter(row["repo"] for row in rows),
        "by_scanner": Counter(row["scanner"] for row in rows),
        "by_dimension": Counter(row["dimension"] for row in rows),
        "by_severity": Counter(str(row["severity"]).lower() for row in rows),
    }
    Path(args.summary_json).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Consolidated findings: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
