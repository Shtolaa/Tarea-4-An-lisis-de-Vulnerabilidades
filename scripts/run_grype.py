#!/usr/bin/env python3
"""Scan generated SBOMs with Grype."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-json", default="data/top_repos.json")
    parser.add_argument("--sbom-dir", default="data/sbom")
    parser.add_argument("--out-dir", default="reports/grype")
    args = parser.parse_args()

    if not shutil.which("grype"):
        raise SystemExit("grype is required. Install it before scanning SBOMs.")

    repos_doc = json.loads(Path(args.repos_json).read_text(encoding="utf-8"))
    sbom_dir = Path(args.sbom_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for repo in repos_doc["repositories"]:
        name = repo["name"]
        sbom = sbom_dir / f"{name}.cyclonedx.json"
        if not sbom.exists():
            print(f"Missing SBOM for {name}: {sbom}", file=sys.stderr)
            continue
        output = out_dir / f"{name}.grype.json"
        command = ["grype", f"sbom:{sbom}", "-o", "json", "--file", str(output)]
        print("+ " + " ".join(str(part) for part in command))
        subprocess.run(command, check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
