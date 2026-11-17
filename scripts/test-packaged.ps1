param(
  [Parameter(Mandatory=$true)][string]$InstallRoot,
  [Parameter(Mandatory=$true)][string]$Test,
  [Parameter(Mandatory=$true)][string]$Label
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$candidateRoot = (Resolve-Path -LiteralPath $InstallRoot).Path
if (Get-Process FileConverter -ErrorAction SilentlyContinue) {
  throw 'Close the existing File Converter first; the test does not terminate user instances.'
}
$nodeExecutable = (Get-Command node).Source
$previousPath = $env:PATH
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9222'
$env:WEBVIEW2_USER_DATA_FOLDER = Join-Path $projectRoot ".tools/$Label-webview"
Remove-Item Env:WEBVIEW2_BROWSER_EXECUTABLE_FOLDER -ErrorAction SilentlyContinue
$env:FILE_CONVERTER_INSTALL_ROOT = $candidateRoot
$env:FILE_CONVERTER_CONTEXT_UNINSTALL_TEST = '0'
$env:FILE_CONVERTER_SHUTDOWN_AFTER_TEST = '1'
$env:FILE_CONVERTER_NATIVE_REPORT = "test-results/$Label-editors.json"
$env:FILE_CONVERTER_NATIVE_SCREENSHOT = "test-results/$Label-editor.png"
$env:FILE_CONVERTER_SMOKE_REPORT = "test-results/$Label-core.json"
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
try {
  $candidate = Start-Process -FilePath (Join-Path $candidateRoot 'FileConverter.exe') -WindowStyle Hidden -PassThru
} finally { $env:PATH = $previousPath }
$ready = $false
for ($attempt = 0; $attempt -lt 80; $attempt++) {
  try {
    $null = Invoke-RestMethod 'http://127.0.0.1:9222/json/version' -TimeoutSec 1
    $ready = $true
    break
  } catch { Start-Sleep -Milliseconds 250 }
}
if (!$ready) { throw 'Candidate CDP did not become ready; leave the candidate available for inspection.' }
$processes = @(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -in @('FileConverter.exe','FileConverterEngine.exe','msedgewebview2.exe') -and
  $_.ExecutablePath -and $_.ExecutablePath.StartsWith($candidateRoot, [StringComparison]::OrdinalIgnoreCase)
} | Select-Object ProcessId, Name, ExecutablePath)
if (!($processes | Where-Object {$_.Name -eq 'msedgewebview2.exe' -and $_.ExecutablePath -like '*webview-runtime*'})) {
  throw 'Fixed WebView2 was not selected from the candidate payload.'
}
$processes | ConvertTo-Json -Depth 3 | Set-Content "test-results/$Label-processes.json"
& $nodeExecutable $Test *> "test-results/$Label.log"
$testExit = $LASTEXITCODE
$null = $candidate.WaitForExit(15000)
if (!$candidate.HasExited) { throw 'Candidate did not exit normally after test.' }
$survivors = @(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq 'FileConverterEngine.exe' -and $_.ExecutablePath -and
  $_.ExecutablePath.StartsWith($candidateRoot, [StringComparison]::OrdinalIgnoreCase)
})
if ($survivors.Count) { throw 'Candidate left sidecar processes running.' }
if ($testExit) { throw "Test failed ($testExit); see test-results/$Label.log" }
Write-Output "PASS $Label; app-local Fixed WebView2, system-only child PATH, normal process-tree exit."
