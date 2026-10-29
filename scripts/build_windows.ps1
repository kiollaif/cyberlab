# Отдельная сборка EXE для разработчика. Пользователю готового EXE Python/uv не нужны.
$ErrorActionPreference = "Stop"
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw "Build this EXE on Windows. PyInstaller does not cross-compile."
}
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    uv sync --locked --group build
    if ($LASTEXITCODE -ne 0) { throw "Dependency sync failed" }
    uv run --locked --group build python scripts/build_desktop.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
    uv run --locked python scripts/verify_desktop.py dist/desktop/CyberLab.exe --report dist/desktop/windows-portable-smoke.json
    if ($LASTEXITCODE -ne 0) { throw "Standalone EXE verification failed" }
} finally {
    Pop-Location
}
