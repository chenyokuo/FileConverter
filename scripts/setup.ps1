param(
    [string]$PythonExe='python', [string]$DownloadCache='', [string]$WheelCache='',
    [string]$NpmCli='', [switch]$Offline, [switch]$SkipDependencies,
    [switch]$InitializeSigningKey
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
if (!$SkipDependencies) {
    $parameters=@{PythonExe=$PythonExe;DownloadCache=$DownloadCache;WheelCache=$WheelCache;NpmCli=$NpmCli;Offline=$Offline}
    & "$PSScriptRoot/setup-dependencies.ps1" @parameters
}
if ($InitializeSigningKey) { . "$PSScriptRoot/signing.ps1"; Initialize-UpdateSigning }
Write-Host 'Setup complete. No installer built, no system file associations changed.'
