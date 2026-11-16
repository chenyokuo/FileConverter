param([switch]$SkipTests, [switch]$NoInstaller)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $ProjectRoot
if (Test-Path '.tools\cargo\bin') {
    $env:RUSTUP_HOME = Join-Path $ProjectRoot '.tools\rustup'
    $env:CARGO_HOME = Join-Path $ProjectRoot '.tools\cargo'
    $env:PATH = (Join-Path $ProjectRoot '.tools\cargo\bin') + ';' + (Join-Path $ProjectRoot '.tools') + ';' + $env:PATH
}
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (!(Test-Path $PythonExe)) { throw 'Run python -m venv .venv and install engine/requirements-lock.txt first.' }
function Invoke-Checked {
    param([scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Build command failed with exit code $LASTEXITCODE" }
}
Invoke-Checked { & $PythonExe scripts\icons.py }
if (!(Test-Path 'vendor\ffmpeg\ffprobe.exe')) { Invoke-Checked { & $PythonExe scripts\prepare.py } }
Invoke-Checked { & $PythonExe scripts\freeze.py }
Invoke-Checked { node tests\appearance-settings.mjs }
if (!$SkipTests) {
    Invoke-Checked { & $PythonExe tests\test_engine.py }
    $env:RAI_TEST_FROZEN = Join-Path $ProjectRoot 'src-tauri\binaries\rai-engine\rai-engine.exe'
    try { Invoke-Checked { & $PythonExe tests\test_engine.py } }
    finally { Remove-Item Env:RAI_TEST_FROZEN -ErrorAction SilentlyContinue }
}
Invoke-Checked { & $PythonExe scripts\licenses.py }
if ($NoInstaller) { Invoke-Checked { npm run package -- --no-bundle } }
else { Invoke-Checked { npm run package } }
Invoke-Checked { & $PythonExe scripts\portable.py }
Write-Host 'Build finished. See release/ and docs/VALIDATION.md for tested scope.'
