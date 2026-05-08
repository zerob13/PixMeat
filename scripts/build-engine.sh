#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/engine"
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller beauty_engine/cli_entry.py --name beauty-engine --onefile --clean --noconfirm
