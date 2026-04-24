#!/usr/bin/env bash
set -euo pipefail

ORG="${ORG:-FlowiseAI}"
TOP="${TOP:-5}"
SKIP_CODEQL="${SKIP_CODEQL:-0}"
REFRESH_REPOS="${REFRESH_REPOS:-0}"

cd "$(dirname "${BASH_SOURCE[0]}")/.."

run_step() {
    local name="$1"
    shift
    printf '\n== %s ==\n' "$name"
    "$@"
}

run_step "Check prerequisites" \
    python scripts/check_prereqs.py

run_step "Mine top repositories with GitHub API" \
    python scripts/mine_github_repos.py --org "$ORG" --top "$TOP"

if [ "$REFRESH_REPOS" = "1" ]; then
    run_step "Clone or refresh selected repositories" \
        python scripts/clone_repos.py --refresh
else
    run_step "Clone selected repositories" \
        python scripts/clone_repos.py
fi

run_step "Generate CycloneDX SBOMs with Syft" \
    python scripts/generate_sbom.py

run_step "Scan SBOMs with Grype" \
    python scripts/run_grype.py

if [ "$SKIP_CODEQL" != "1" ]; then
    run_step "Analyze source code with CodeQL" \
        python scripts/run_codeql.py
fi

run_step "Inspect GitHub Actions workflows" \
    python scripts/analyze_ci.py

run_step "Consolidate dataset" \
    python scripts/consolidate_findings.py

printf '\nDone. Main outputs:\n'
printf -- '- data/top_repos.csv\n'
printf -- '- data/sbom/*.cyclonedx.json\n'
printf -- '- reports/grype/*.grype.json\n'
printf -- '- reports/codeql/*.sarif\n'
printf -- '- reports/ci/ci_findings.csv\n'
printf -- '- data/findings.csv\n'
printf -- '- data/summary.json\n'
