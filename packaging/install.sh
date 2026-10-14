#!/usr/bin/env bash
# Usage: packaging/install.sh [--uninstall]  (adds the app launcher, icon and login autostart for the current user)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ID="dev.harsha.RoutineTracker"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
AUTOSTART="$HOME/.config/autostart"

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -f "$APPS/$ID.desktop" "$ICONS/$ID.svg" "$AUTOSTART/$ID.desktop"
  echo "Removed launcher, icon and autostart (your data in $ROOT/data is untouched)."
  exit 0
fi

mkdir -p "$APPS" "$ICONS" "$AUTOSTART"
cp "$ROOT/packaging/$ID.svg" "$ICONS/$ID.svg"
sed "s|@ROOT@|$ROOT|" "$ROOT/packaging/$ID.desktop.in" > "$APPS/$ID.desktop"
sed "s|@ROOT@|$ROOT|; s|^Exec=.*|Exec=python3 -m routine_tracker --background|" "$ROOT/packaging/$ID.desktop.in" > "$AUTOSTART/$ID.desktop"
chmod +x "$APPS/$ID.desktop"
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" || true
echo "Installed. Search 'Routine Tracker' in your app menu. It starts in the background at next login."
