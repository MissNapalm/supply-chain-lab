#!/bin/sh
# Detection helper — run DURING an install to catch the lifecycle-script callout.
# macOS (lsof) + Linux (ss) both covered. Flags node/python sockets to the lab port.
PORT="${LAB_PORT:-4444}"
echo "[*] Watching for install-time outbound connections to :$PORT (Ctrl-C to stop)"
while true; do
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -i TCP:"$PORT" 2>/dev/null | grep -Ei 'node|python' \
      && echo "    ^ lifecycle-script callout detected $(date '+%H:%M:%S')"
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -tnp 2>/dev/null | grep ":$PORT" | grep -Ei 'node|python' \
      && echo "    ^ lifecycle-script callout detected $(date '+%H:%M:%S')"
  fi
  sleep 0.3
done
