#!/usr/bin/env python3
"""Check local tools required by the vulnerability analysis pipeline."""

from __future__ import annotations

import shutil
import subprocess
import sys


TOOLS = ["git", "python", "syft", "grype", "codeql"]


def version(command: str) -> str:
    candidates = {
        "codeql": [command, "version"],
        "python": [command, "--version"],
    }
    args = candidates.get(command, [command, "--version"])
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        return f"found, but version check failed: {exc}"
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0] if output else "found"


def main() -> int:
    missing: list[str] = []
    for tool in TOOLS:
        path = shutil.which(tool)
        if not path:
            missing.append(tool)
            print(f"[missing] {tool}")
            continue
        print(f"[ok] {tool}: {version(tool)}")

    if missing:
        print("")
        print("Missing tools: " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
