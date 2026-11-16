# File Converter development workflow

Continue this existing project. Preserve working conversions, the queue, settings,
history, and the application identifier `studio.rai.converter`.

## P0–P4 validation

- Use development mode, relevant unit tests, necessary integration tests, and
  incremental compilation checks. Keep a test record and Git commit per phase.
- Do not rebuild a Windows Installer or Portable ZIP for each feature or phase.
- Intermediate packaging is allowed only when changing Tauri packaging settings,
  Sidecar/Runtime deployment, or when installation-environment verification is
  actually required. Record the reason.
- Reuse installed dependencies and caches. Do not repeat downloads or unrelated
  full test suites. Repeat checks only for changed behavior or unresolved failures.
- Existing P0 icon/deployment validation artifacts are preview snapshots. Later
  source commits do not imply that those artifacts were repackaged.

## P5 release

After all requested features are complete, perform the consolidated Release Build,
Windows Installer, Portable ZIP, deployment checks, and final acceptance testing.
Keep clean-machine and physical DPI limitations explicit.

## Identity, icons, and publication

- The product is File Converter; its main executable is FileConverter.exe.
- Preserve the supplied icon original and user-data compatibility.
- Only update this application's icons and shortcuts. Never change other apps,
  Windows default applications, global file-type icons, or file associations.
- Do not push to GitHub before the user's final integration acceptance. Local
  phase commits are authorized. Keep credentials, caches, test files, engines,
  and build artifacts out of Git.

The user's latest explicit instructions take precedence over this workflow.
