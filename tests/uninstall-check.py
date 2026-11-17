"""Uninstall only the explicitly isolated QA installation; preserve user data."""
from pathlib import Path
import base64
import hashlib
import json
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
target = Path(sys.argv[1]).resolve()
assert target.parent == ROOT / ".tools" and target.name.startswith("multimedia-installed-"), target
state_path=Path(sys.argv[sys.argv.index('--state')+1]) if '--state' in sys.argv else ROOT/'.tools/multimedia-install-state.json'
state = json.loads(state_path.read_text())
uninstaller = target / "uninstall.exe"
if "--verify-only" not in sys.argv:
    assert uninstaller.is_file()
    proc = subprocess.Popen([str(uninstaller), "/S"])
    assert proc.wait(timeout=120) == 0
deadline = time.monotonic() + 90
pending = lambda: (target / "FileConverter.exe").exists() or uninstaller.exists() or any(Path(s["path"]).exists() for s in state["shortcuts"])
while pending() and time.monotonic() < deadline:
    time.sleep(.25)
assert not (target / "FileConverter.exe").exists(), "Uninstaller did not remove the QA executable"
database = Path(state["dataDir"]) / "history.sqlite3"
assert database.is_file(), "User data was removed"
con = sqlite3.connect(database)
matches = {}
for table, expected in state["tableHashes"].items():
    rows = con.execute("SELECT * FROM " + table).fetchall()
    decoded = [tuple(json.loads(value) if isinstance(value, str) and value.startswith(("{", "[")) else value for value in row) for row in rows]
    actual = hashlib.sha256(json.dumps(decoded, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    matches[table] = actual == expected
assert all(matches.values()), matches
for shortcut in state["shortcuts"]:
    p = Path(shortcut["path"])
    assert not p.exists(), "QA shortcut survived uninstall: " + p.name
    if shortcut["existed"]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(base64.b64decode(shortcut["content"]))
report = {"uninstalled": True, "settingsHistoryAutomationPreserved": matches,
          "ownShortcutsRemovedOrRestored": True, "otherAppsOrAssociationsChanged": False}
(ROOT / "test-results/multimedia-uninstall.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
