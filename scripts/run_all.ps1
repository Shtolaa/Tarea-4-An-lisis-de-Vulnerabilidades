param(
    [string]$Org = "FlowiseAI",
    [int]$Top = 5,
    [switch]$SkipCodeQL,
    [switch]$RefreshRepos
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Host ""
    Write-Host "== $Name ==" -ForegroundColor Cyan
    & $Command
}

Run-Step "Check prerequisites" {
    python scripts/check_prereqs.py
}

Run-Step "Mine top repositories with GitHub API" {
    python scripts/mine_github_repos.py --org $Org --top $Top
}

if ($RefreshRepos) {
    Run-Step "Clone or refresh selected repositories" {
        python scripts/clone_repos.py --refresh
    }
} else {
    Run-Step "Clone selected repositories" {
        python scripts/clone_repos.py
    }
}

Run-Step "Generate CycloneDX SBOMs with Syft" {
    python scripts/generate_sbom.py
}

Run-Step "Scan SBOMs with Grype" {
    python scripts/run_grype.py
}

if (-not $SkipCodeQL) {
    Run-Step "Analyze source code with CodeQL" {
        python scripts/run_codeql.py
    }
}

Run-Step "Inspect GitHub Actions workflows" {
    python scripts/analyze_ci.py
}

Run-Step "Consolidate dataset" {
    python scripts/consolidate_findings.py
}

Write-Host ""
Write-Host "Done. Main outputs:" -ForegroundColor Green
Write-Host "- data/top_repos.csv"
Write-Host "- data/sbom/*.cyclonedx.json"
Write-Host "- reports/grype/*.grype.json"
Write-Host "- reports/codeql/*.sarif"
Write-Host "- reports/ci/ci_findings.csv"
Write-Host "- data/findings.csv"
Write-Host "- data/summary.json"
