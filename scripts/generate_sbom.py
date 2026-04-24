#!/usr/bin/env python3
"""Generate CycloneDX JSON SBOMs for each cloned repository using Syft."""

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
    parser.add_argument("--repos-dir", default="data/repos")
    parser.add_argument("--out-dir", default="data/sbom")
    args = parser.parse_args()

    if not shutil.which("syft"):
        raise SystemExit("syft is required. Install it before generating SBOMs.")

    repos_doc = json.loads(Path(args.repos_json).read_text(encoding="utf-8"))
    repos_dir = Path(args.repos_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for repo in repos_doc["repositories"]:
        name = repo["name"]
        source = repos_dir / name
        if not source.exists():
            print(f"Missing clone for {name}: {source}", file=sys.stderr)
            continue
        output = out_dir / f"{name}.cyclonedx.json"
        command = ["syft", f"dir:{source}", "-o", f"cyclonedx-json={output}"]
        print("+ " + " ".join(str(part) for part in command))
        subprocess.run(command, check=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
