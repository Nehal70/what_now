# Removes stray root-level directories left after the frontend/ monorepo move.
# Safe to re-run. Canonical paths: frontend/agent, frontend/moss-hacker-starter

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $root "frontend\package.json"))) {
    $root = Resolve-Path (Join-Path $PSScriptRoot "..")
}

$targets = @(
    (Join-Path $root "agent"),
    (Join-Path $root "moss-hacker-starter")
)

foreach ($path in $targets) {
    if (-not (Test-Path $path)) {
        Write-Host "Already gone: $path"
        continue
    }

    for ($i = 0; $i -lt 5; $i++) {
        cmd /c "rmdir /s /q `"$path`"" 2>$null
        if (-not (Test-Path $path)) {
            Write-Host "Removed: $path"
            break
        }
        Start-Sleep -Seconds 2
    }

    if (Test-Path $path) {
        Write-Warning "Could not remove $path (directory in use). Close terminals using that path and re-run."
    }
}
