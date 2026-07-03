param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SpecPath = Join-Path $ProjectRoot "InstitutionalBounceScreener.spec"
$OutputPath = Join-Path $ProjectRoot "dist"
$BuildPath = Join-Path $ProjectRoot "build"

Set-Location $ProjectRoot

if ($Clean) {
    if (Test-Path $OutputPath) { Remove-Item -LiteralPath $OutputPath -Recurse -Force }
    if (Test-Path $BuildPath) { Remove-Item -LiteralPath $BuildPath -Recurse -Force }
}

if (-not (Test-Path $SpecPath)) {
    throw "Missing PyInstaller spec: $SpecPath"
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python -m PyInstaller $SpecPath --noconfirm

Write-Host "Release build output: $OutputPath"
