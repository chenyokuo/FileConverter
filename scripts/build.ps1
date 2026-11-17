param([switch]$SkipTests, [switch]$NoInstaller, [string]$PythonExe='')
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $ProjectRoot
if (Test-Path '.tools\cargo\bin') {
    $env:RUSTUP_HOME = Join-Path $ProjectRoot '.tools\rustup'
    $env:CARGO_HOME = Join-Path $ProjectRoot '.tools\cargo'
    $env:PATH = (Join-Path $ProjectRoot '.tools\cargo\bin') + ';' + (Join-Path $ProjectRoot '.tools') + ';' + $env:PATH
}
function Invoke-Npm {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$NpmArgs)
    if($env:FILE_CONVERTER_NPM_CLI){node $env:FILE_CONVERTER_NPM_CLI @NpmArgs}
    elseif(Test-Path '.tools/npm/package/bin/npm-cli.js'){node .tools/npm/package/bin/npm-cli.js @NpmArgs}
    else{npm @NpmArgs}
}
if (!$PythonExe) { $PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe' }
$PythonExe = [IO.Path]::GetFullPath($PythonExe)
if (!(Test-Path $PythonExe)) { throw 'Run python -m venv .venv and install engine/requirements-lock.txt first.' }
function Invoke-Checked {
    param([scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Build command failed with exit code $LASTEXITCODE" }
}
if (!(Test-Path 'vendor\ffmpeg\ffprobe.exe')) { Invoke-Checked { & $PythonExe scripts\prepare.py } }
Invoke-Checked { & $PythonExe scripts\acquire_engines.py }
Invoke-Checked { & $PythonExe scripts\verify_dependencies.py }
Invoke-Checked { & $PythonExe scripts\stage_runtime.py }
Invoke-Checked { & $PythonExe scripts\freeze.py }
# A new frozen runtime is a new integration boundary, even when source regressions already passed.
$env:FILE_CONVERTER_TEST_FROZEN=Join-Path $ProjectRoot 'src-tauri/binaries/FileConverterEngine/FileConverterEngine.exe'
$env:FILE_CONVERTER_TEST_ENGINES=Join-Path $ProjectRoot 'src-tauri/bundled-engines'
try {
    Invoke-Checked { & $PythonExe -X utf8 -m unittest discover -s tests -p 'test_image_editor.py' -v }
    Invoke-Checked { & $PythonExe -X utf8 -m unittest discover -s tests -p 'test_video_editor.py' -v }
    Invoke-Checked { & $PythonExe -X utf8 -m unittest discover -s tests -p 'test_audio_links.py' -v }
    Invoke-Checked { & $PythonExe -X utf8 -m unittest discover -s tests -p 'test_download_preview.py' -v }
    Invoke-Checked { & $PythonExe -X utf8 -m unittest discover -s tests -p 'test_p2.py' -k ocr -v }
    Invoke-Checked { & $PythonExe -X utf8 -m unittest discover -s tests -p 'test_p4.py' -k pdf_ocr -v }
} finally { Remove-Item Env:FILE_CONVERTER_TEST_FROZEN,Env:FILE_CONVERTER_TEST_ENGINES -ErrorAction SilentlyContinue }

Invoke-Checked { node tests\appearance-settings.mjs }
if (!$SkipTests) {
    Invoke-Checked { & $PythonExe -X utf8 -m unittest discover -s tests -p 'test_*.py' -v }
    Invoke-Checked { & $PythonExe -X utf8 tests\matrix.py }
    $env:FILE_CONVERTER_TEST_FROZEN = Join-Path $ProjectRoot 'src-tauri\binaries\FileConverterEngine\FileConverterEngine.exe'
    $env:FILE_CONVERTER_TEST_ENGINES = Join-Path $ProjectRoot 'src-tauri\bundled-engines'
    try {
        Invoke-Checked { & $PythonExe tests\test_engine.py }
        Invoke-Checked { & $PythonExe -X utf8 -m unittest discover -s tests -p 'test_p[234].py' -v }
    }
    finally { Remove-Item Env:FILE_CONVERTER_TEST_FROZEN,Env:FILE_CONVERTER_TEST_ENGINES -ErrorAction SilentlyContinue }
}
Invoke-Checked { & $PythonExe scripts\licenses.py }
Invoke-Checked { & $PythonExe scripts\normalize_bundle_marker.py }
if ($NoInstaller) { Invoke-Checked { Invoke-Npm run package -- --no-bundle } }
else { Invoke-Checked { Invoke-Npm run package } }
$IconTargets = @('src-tauri\target\release\FileConverter.exe', 'src-tauri\binaries\FileConverterEngine\FileConverterEngine.exe')
if (!$NoInstaller) {
    $BuildVersion = (Get-Content package.json -Raw | ConvertFrom-Json).version
    $IconTargets += "src-tauri\target\release\bundle\nsis\File Converter_${BuildVersion}_x64-setup.exe"
}
Invoke-Checked { & $PythonExe tests\test_icons.py @IconTargets }
if ($NoInstaller) { Invoke-Checked { & $PythonExe scripts\portable.py --no-installer } }
else { Invoke-Checked { & $PythonExe scripts\portable.py } }
Write-Host 'Build finished. See release/ and docs/VALIDATION.md for tested scope.'
