#!/usr/bin/env bash
# Full-screen "PATCH IS ON" fireworks splash — runs ~3 minutes, then ends.
# Usage: ./splash/launch.sh
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
page="file://${here}/patch-is-on.html"

echo "🎆 Launching PATCH IS ON splash (3-minute show)…"

# Prefer a real kiosk/full-screen browser if available, else fall back to xdg-open.
if command -v chromium >/dev/null 2>&1; then
  exec chromium --start-fullscreen --kiosk --new-window "$page"
elif command -v chromium-browser >/dev/null 2>&1; then
  exec chromium-browser --start-fullscreen --kiosk --new-window "$page"
elif command -v google-chrome >/dev/null 2>&1; then
  exec google-chrome --start-fullscreen --kiosk --new-window "$page"
elif command -v firefox >/dev/null 2>&1; then
  exec firefox --kiosk "$page"
elif command -v xdg-open >/dev/null 2>&1; then
  echo "No kiosk browser found — opening in default browser (press F for fullscreen)."
  exec xdg-open "$page"
elif command -v open >/dev/null 2>&1; then          # macOS
  exec open "$page"
else
  echo "Open this file in a browser and press F for fullscreen:"
  echo "  $page"
fi
