$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Engine = Join-Path $Root "engine"
Push-Location $Engine
try {
  python -m pip install -r requirements.txt
  python -m pip install pyinstaller
  python -m PyInstaller beauty_engine/cli_entry.py --name beauty-engine --onefile --clean --noconfirm
}
finally {
  Pop-Location
}
