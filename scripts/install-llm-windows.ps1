<#
Install llama-cpp-python (pre-built CPU wheel) on Windows.
Usage (PowerShell as the same venv environment):
  .\install-llm-windows.ps1

This script prefers the pre-built CPU wheel index maintained by the llama-cpp-python
community to avoid requiring a C++ toolchain on Windows.
#>

param(
    [string]$ExtraIndex = "https://abetlen.github.io/llama-cpp-python/whl/cpu",
    [string]$Package = "llama-cpp-python",
    [switch]$PreferBinary
)

Write-Host "Installing $Package (Windows pre-built wheel)" -ForegroundColor Cyan

$pref = ""
if ($PreferBinary) { $pref = "--prefer-binary" }

$cmd = "pip install $Package $pref --extra-index-url $ExtraIndex"
Write-Host "Running: $cmd"

$proc = Start-Process -FilePath powershell -ArgumentList "-NoProfile -Command $cmd" -NoNewWindow -PassThru -Wait
if ($proc.ExitCode -ne 0) {
    Write-Host "Installation failed (exit code $($proc.ExitCode))." -ForegroundColor Red
    exit $proc.ExitCode
}

Write-Host "Installation finished. Verify by running: python -c \"import llama_cpp; print('ok')\"" -ForegroundColor Green
exit 0
