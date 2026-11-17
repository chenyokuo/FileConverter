# Dot-source from setup/publish. Secrets stay DPAPI-encrypted for this Windows user.
$SigningRoot = Join-Path $env:LOCALAPPDATA 'FileConverter/Signing'
function Initialize-UpdateSigning {
    $root = Split-Path $PSScriptRoot -Parent
    $protected = Join-Path $SigningRoot 'updater-private.dpapi'
    if (Test-Path -LiteralPath $protected) { return }
    $configPath = Join-Path $root 'src-tauri/tauri.conf.json'
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if ($config.plugins.updater.pubkey) { throw 'A public key is already configured. Restore its matching private key; do not rotate it silently.' }
    New-Item -ItemType Directory -Force -Path $SigningRoot | Out-Null
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls $SigningRoot /inheritance:r /grant:r "${identity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
    if ($LASTEXITCODE) { throw 'Cannot restrict signing directory ACL' }
    $temporary = Join-Path $SigningRoot 'generated.key'
    if (Test-Path -LiteralPath $temporary) { throw 'Unfinished key generation exists; inspect the private signing directory.' }
    try {
        $generated = & node (Join-Path $root 'node_modules/@tauri-apps/cli/tauri.js') signer generate --ci -p '' -w $temporary 2>&1
        if ($LASTEXITCODE) { throw 'Tauri signing-key generation failed (secret output suppressed).' }
        $key = Get-Content -LiteralPath $temporary -Raw
        ConvertTo-SecureString $key -AsPlainText -Force | ConvertFrom-SecureString | Set-Content -LiteralPath $protected
        $public = (Get-Content -LiteralPath ($temporary+'.pub') -Raw).Trim()
        if (!$config.plugins) { $config | Add-Member -NotePropertyName plugins -NotePropertyValue ([pscustomobject]@{}) }
        $config.plugins | Add-Member -Force -NotePropertyName updater -NotePropertyValue ([pscustomobject]@{pubkey=$public;endpoints=@();windows=@{installMode='passive'}})
        $config | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $configPath -Encoding utf8
        Set-Content -LiteralPath (Join-Path $root 'config/updater.pub') -Value $public -Encoding ascii
        Write-Host 'Generated update identity. Private key is protected by Windows DPAPI; back it up securely before changing machines.'
    } finally {
        $key=$null; $generated=$null
        # Exact files owned by this invocation; never recurse or touch another key.
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
        if (Test-Path -LiteralPath ($temporary+'.pub')) { Remove-Item -LiteralPath ($temporary+'.pub') }
    }
}
function Enable-UpdateSigning {
    if ($env:TAURI_SIGNING_PRIVATE_KEY) { return }
    $protected = Join-Path $SigningRoot 'updater-private.dpapi'
    if (!(Test-Path -LiteralPath $protected)) { throw 'No signing key. Restore the matching key or run scripts/setup.ps1 -InitializeSigningKey for the first release.' }
    $secure = ConvertTo-SecureString -String ((Get-Content -LiteralPath $protected -Raw).Trim())
    $env:TAURI_SIGNING_PRIVATE_KEY = [Net.NetworkCredential]::new('', $secure).Password
    $env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = ''
}
