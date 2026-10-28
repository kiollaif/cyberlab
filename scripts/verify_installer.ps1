# Проверяем настоящую тихую установку, ярлыки, запуск и удаление без потери данных.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $root "dist\desktop\CyberLab-Setup.exe"
$target = Join-Path $env:TEMP "CyberLab installed test"
$report = Join-Path $root "dist\desktop\windows-installed-smoke.json"
$log = Join-Path $root "dist\desktop\installer.log"
$process = Start-Process $installer -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DIR=`"$target`"", "/LOG=`"$log`"") -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Installer exit $($process.ExitCode)" }
$installed = Join-Path $target "CyberLab.exe"
if (!(Test-Path $installed)) { throw "Installed executable is missing" }
$shell = New-Object -ComObject WScript.Shell
$shortcuts = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "CYBERLAB.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "CYBERLAB\CYBERLAB.lnk")
)
foreach ($shortcut in $shortcuts) {
    if (!(Test-Path $shortcut)) { throw "Missing shortcut: $shortcut" }
    if ($shell.CreateShortcut($shortcut).TargetPath -ne $installed) { throw "Wrong shortcut target" }
}
uv run --locked python scripts/verify_desktop.py $installed --report $report
if ($LASTEXITCODE -ne 0) { throw "Installed application smoke test failed" }
$data = Get-Content $report -Raw | ConvertFrom-Json
$marker = Join-Path $data.data_directory "installer-data-preservation-test.txt"
New-Item -ItemType Directory -Force (Split-Path $marker) | Out-Null
Set-Content $marker "History must survive uninstall" -Encoding UTF8
$process = Start-Process (Join-Path $target "unins000.exe") -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Uninstaller exit $($process.ExitCode)" }
if (!(Test-Path $marker)) { throw "Uninstaller deleted user data" }
foreach ($shortcut in $shortcuts) {
    if (Test-Path $shortcut) { throw "Uninstaller left a shortcut: $shortcut" }
}
Remove-Item $marker
Write-Output "Installer, both shortcuts, installed GUI, uninstall and data preservation passed."
