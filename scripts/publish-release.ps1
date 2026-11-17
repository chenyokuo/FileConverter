param(
    [string]$Version='', [string]$NotesFile='', [switch]$SkipBuild,
    [switch]$PrepareOnly, [switch]$DraftOnly, [switch]$RunFullRegression,
    [string]$PythonExe=''
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
function Checked([scriptblock]$Run){& $Run;if($LASTEXITCODE){throw "Release command failed: $LASTEXITCODE"}}
$gh=if(Get-Command gh -ErrorAction SilentlyContinue){(Get-Command gh).Source}else{Join-Path $root '.tools/gh/bin/gh.exe'}
if (!(Test-Path -LiteralPath $gh)) { throw 'GitHub CLI is required. Install gh and run gh auth login; never put a token in this repository.' }
Checked { & $gh auth status }
$current=(Get-Content package.json -Raw|ConvertFrom-Json).version
if(!$Version){$Version=$current}
if($Version -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$'){throw 'Invalid SemVer'}
if(!$NotesFile){$NotesFile=Join-Path $root "docs/releases/$Version.md"}
if(!(Test-Path -LiteralPath $NotesFile)){throw "Release notes are required: $NotesFile"}
if(git status --porcelain){throw 'Commit source changes before publishing. Build provenance must match a clean commit.'}
if($Version -ne $current){
    Checked {node scripts/release.mjs version $Version}
    Checked {git add -- package.json package-lock.json src-tauri/Cargo.toml src-tauri/Cargo.lock src-tauri/tauri.conf.json}
    Checked {git commit -m "build: prepare $Version"}
}
Checked {node scripts/release.mjs check}
$source=(git rev-parse HEAD).Trim()
Checked {git fetch origin}
if(!$PrepareOnly){
    $repo=(& $gh repo view chenyokuo/FileConverter --json isPrivate|ConvertFrom-Json)
    if($repo.isPrivate){throw 'The update repository is private. Make chenyokuo/FileConverter public before publishing anonymous updater endpoints.'}
    if((git branch --show-current).Trim() -ne 'main'){throw 'Publish from validated main; do not silently merge feature branches.'}
    if((git rev-parse origin/main).Trim() -ne $source){throw 'Push validated main before publishing.'}
    $published=& $gh release view "v$Version" --repo chenyokuo/FileConverter --json isDraft 2>$null
    if($LASTEXITCODE -eq 0 -and !($published|ConvertFrom-Json).isDraft){throw 'This version is already public. Choose a new version; do not rebuild or replace it.'}
}
. "$PSScriptRoot/signing.ps1"
$oldKey=$env:TAURI_SIGNING_PRIVATE_KEY;$oldPassword=$env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD;$oldCI=$env:CI
try {
    Enable-UpdateSigning
    $env:CI='true'
    if(!$SkipBuild){ & "$PSScriptRoot/build.ps1" -SkipTests:(!$RunFullRegression) -PythonExe $PythonExe }
    $directory=Join-Path $root "release/$Version"
    New-Item -ItemType Directory -Force -Path $directory|Out-Null
    $infoPath=Join-Path $directory 'BUILD-INFO.json'
    $buildSource=$source
    if($SkipBuild){
        if(!(Test-Path -LiteralPath $infoPath)){throw 'No prepared build provenance. Run -PrepareOnly once before resuming with -SkipBuild.'}
        $prepared=Get-Content -LiteralPath $infoPath -Raw|ConvertFrom-Json
        if($prepared.version -ne $Version){throw 'Prepared artifact version differs'}
        $buildSource=$prepared.sourceCommit
        $changed=git diff --name-only $buildSource HEAD -- src package.json package-lock.json src-tauri scripts/build.ps1 scripts/portable.py scripts/freeze.py
        if($changed){throw 'Product/build source changed since preparation. Do not publish stale artifacts.'}
    }
    $exe=Join-Path $root 'src-tauri/target/release/FileConverter.exe'
    $binaryVersion=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe).ProductVersion
    if($binaryVersion -notlike "$Version*"){throw "Built EXE version is $binaryVersion, expected $Version"}
    $installer="File Converter_${Version}_x64-setup.exe";$portable="FileConverter-${Version}-windows-x64-portable.zip"
    foreach($name in @($installer,$portable)){
        $artifact=Join-Path $root "release/$name"
        if(!(Test-Path -LiteralPath $artifact)){throw "Missing artifact: $artifact"}
        Copy-Item -LiteralPath $artifact -Destination (Join-Path $directory $name) -Force
        # Both NSIS and Portable carry signatures bound to their actual version.
        Checked { node node_modules/@tauri-apps/cli/tauri.js signer sign --app-version $Version $artifact }
        Copy-Item -LiteralPath ($artifact+'.sig') -Destination (Join-Path $directory ($name+'.sig')) -Force
        $verification=Start-Process -FilePath $exe -ArgumentList @('--verify-release-signature',('"'+$artifact+'"'),('"'+$artifact+'.sig"'),$Version) -WindowStyle Hidden -Wait -PassThru
        if($verification.ExitCode){throw "Signature/public-key/version verification failed: $name"}
    }
    Checked {node scripts/release.mjs manifest $Version $NotesFile}
    $provenance=@{version=$Version;sourceCommit=$buildSource;publicationCommit=$source;preparedAt=[DateTime]::UtcNow.ToString('o');repository='chenyokuo/FileConverter';channel=$(if($Version.Contains('-')){'rc'}else{'stable'})}
    $provenance|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $directory 'BUILD-INFO.json') -Encoding utf8
    if($PrepareOnly){Write-Host "Signed artifacts prepared: $directory";return}
    $tag="v$Version"
    $existingTag=git rev-parse --verify "refs/tags/$tag" 2>$null
    if($LASTEXITCODE -eq 0){if((git rev-list -n 1 $tag).Trim() -ne $source){throw 'Existing tag points to another commit; never overwrite release tags.'}}
    else{Checked {git tag -a $tag -m "File Converter $Version" $source}}
    Checked {git push origin "refs/tags/$tag"}
    $release=& $gh release view $tag --repo chenyokuo/FileConverter --json isDraft,assets 2>$null
    if($LASTEXITCODE -eq 0){
        $releaseInfo=$release|ConvertFrom-Json
        if(!$releaseInfo.isDraft){throw 'Published releases are immutable; choose a new version instead of replacing public assets.'}
    }else{
        $create=@('release','create',$tag,'--repo','chenyokuo/FileConverter','--verify-tag','--draft','--title',"File Converter $Version",'--notes-file',$NotesFile)
        if($Version.Contains('-')){$create+='--prerelease'}
        Checked {& $gh @create}
    }
    $assets=@($installer,($installer+'.sig'),$portable,($portable+'.sig'),'latest.json','SHA256SUMS.json','SHA256SUMS.txt','BUILD-INFO.json')|ForEach-Object{Join-Path $directory $_}
    # A draft is resumable after an interrupted upload. Published assets are never clobbered.
    Checked {& $gh release upload $tag @assets --repo chenyokuo/FileConverter --clobber}
    if(!$DraftOnly){
        $edit=@('release','edit',$tag,'--repo','chenyokuo/FileConverter','--draft=false','--latest=false')
        if(!$Version.Contains('-')){$edit[-1]='--latest=true'}
        Checked {& $gh @edit}
    }
    Write-Host "https://github.com/chenyokuo/FileConverter/releases/tag/$tag"
    Write-Host "https://github.com/chenyokuo/FileConverter/releases/download/$tag/latest.json"
} finally {
    $env:TAURI_SIGNING_PRIVATE_KEY=$oldKey;$env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD=$oldPassword;$env:CI=$oldCI
}
