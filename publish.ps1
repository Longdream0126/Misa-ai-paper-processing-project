param(
    [Parameter(Mandatory = $true)]
    [string]$Remote,
    [string]$Message = "feat: Misa's AI Paper Processing Project v0.1",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "git was not found. Install it first:" -ForegroundColor Yellow
    Write-Host "  winget install --id Git.Git -e --source winget"
    exit 1
}

Push-Location $PSScriptRoot
try {
    if (-not (Test-Path ".git")) {
        git init -b $Branch | Out-Null
    }
    git add .
    git commit -m $Message
    $existing = git remote 2>$null
    if ($existing -contains "origin") {
        git remote set-url origin $Remote
    } else {
        git remote add origin $Remote
    }
    git push -u origin $Branch
    Write-Host ""
    Write-Host "Pushed to $Remote ($Branch)." -ForegroundColor Green
} finally {
    Pop-Location
}
