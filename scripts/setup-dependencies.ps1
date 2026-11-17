param([string]$PythonExe='python',[string]$DownloadCache='',[string]$WheelCache='',[string]$NpmCli='',[switch]$Offline)
$ErrorActionPreference='Stop'
$ProjectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $ProjectRoot
New-Item -ItemType Directory -Force -Path '.tools','test-results' | Out-Null
$env:PYTHONUTF8='1'
if($Offline){$env:FILE_CONVERTER_OFFLINE='1'}
if($DownloadCache){$env:FILE_CONVERTER_DOWNLOAD_CACHE=[IO.Path]::GetFullPath($DownloadCache)}
if($WheelCache){$env:FILE_CONVERTER_WHEEL_CACHE=[IO.Path]::GetFullPath($WheelCache)}
if($NpmCli){$env:FILE_CONVERTER_NPM_CLI=[IO.Path]::GetFullPath($NpmCli)}
function Checked([scriptblock]$Run){& $Run;if($LASTEXITCODE -ne 0){throw "Dependency command failed: $LASTEXITCODE"}}
Checked {& $PythonExe -c "import sys;assert sys.version_info[:2]==(3,13), 'CPython 3.13 x64 is required';assert sys.maxsize>2**32"}
if(!(Test-Path '.venv/Scripts/python.exe')){Checked {& $PythonExe -m venv .venv};Set-Content -LiteralPath '.venv/.fileconverter-created' -Value 'Created by File Converter setup for the classic non-AI environment'}
$Venv=Join-Path $ProjectRoot '.venv/Scripts/python.exe'
$PipArgs=@('-X','utf8','-m','pip','install','--no-deps','--require-hashes','-r','engine/requirements-hashes.txt')
if($WheelCache){$PipArgs+=@('--find-links',$WheelCache)}
if($Offline){$PipArgs+='--no-index'}
Checked {& $Venv @PipArgs}
Checked {& $Venv -X utf8 scripts/prune_optional_ai.py}
$NodeArgs=@('ci','--no-audit','--no-fund');if($Offline){$NodeArgs+='--offline'}else{$NodeArgs+='--prefer-offline'}
if($NpmCli){Checked {node $NpmCli @NodeArgs}}else{Checked {npm @NodeArgs}}
if(Get-Command cargo -ErrorAction SilentlyContinue){$CargoArgs=@('fetch','--locked','--target','x86_64-pc-windows-msvc','--manifest-path','src-tauri/Cargo.toml');if($Offline){$CargoArgs+='--offline'};Checked {cargo @CargoArgs}}else{throw 'Rust MSVC cargo is required on development/build machines'}
Checked {& $Venv -X utf8 scripts/dependencies.py}
Checked {& $Venv -X utf8 scripts/verify_dependencies.py}
Write-Host 'Pinned dependencies restored and checked. No Release / Installer / Portable built.'
