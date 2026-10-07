#!/bin/sh
# Boot a lab-only npm registry (Verdaccio) and publish the poisoned package to it.
# This is the reproducible stand-in for an "internal registry" — the realistic
# way scenario B delivers the dependency (a victim pulls a version range from a
# registry, not a local file: path).
#
# Everything is bound to 127.0.0.1 and fully offline. Verdaccio itself is fetched
# from PUBLIC npm; the poisoned package is ONLY ever published to this local
# registry, never upstream.
#
# Env:
#   LAB_NPM_PORT          registry port (default 4873, matches victim-app/.npmrc)
#   LAB_VERDACCIO_PIDFILE where to write the Verdaccio pid for later cleanup
set -eu

PORT="${LAB_NPM_PORT:-4873}"
REG="http://127.0.0.1:${PORT}/"
LAB_ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
PIDFILE="${LAB_VERDACCIO_PIDFILE:-$WORK/verdaccio.pid}"

log() { echo "[publish] $*"; }

# 1. Boot Verdaccio unless one is already answering on PORT (reuse a dev one).
if curl -sf "${REG}-/ping" >/dev/null 2>&1; then
  log "registry already up on :$PORT — reusing it"
else
  cat > "$WORK/config.yaml" <<YAML
# Generated at runtime so storage lands somewhere writable (a GitHub runner has
# no /verdaccio). Anonymous publish, no uplink: offline and lab-only.
storage: $WORK/storage
auth: {htpasswd: {file: $WORK/htpasswd, max_users: -1}}
packages: {'**': {access: \$all, publish: \$all, unpublish: \$all}}
listen: 0.0.0.0:$PORT
log: {type: stdout, format: pretty, level: warn}
YAML
  log "booting Verdaccio on :$PORT (storage: $WORK/storage)"
  # --registry pins the fetch of verdaccio itself to public npm, so this works
  # even when the caller's .npmrc points at the (empty) lab registry.
  npx --yes --registry https://registry.npmjs.org/ verdaccio@6 \
      --config "$WORK/config.yaml" >"$WORK/verdaccio.log" 2>&1 &
  echo $! > "$PIDFILE"
  for i in $(seq 1 40); do
    curl -sf "${REG}-/ping" >/dev/null 2>&1 && break
    sleep 1
    if [ "$i" = 40 ]; then
      log "Verdaccio never came up"; cat "$WORK/verdaccio.log"; exit 1
    fi
  done
  log "Verdaccio up (pid $(cat "$PIDFILE"))"
fi

# 2. Publish test_library. Verdaccio allows anonymous publish ($all), but the
#    npm client still insists on *some* token being present — use a dummy one.
export HOME="$WORK"
npm config set "//127.0.0.1:${PORT}/:_authToken" "lab-dummy-token" --location=user
if ( cd "$LAB_ROOT/test_library" && npm publish --registry "$REG" 2>"$WORK/pub.err" ); then
  log "published test_library to $REG"
else
  if grep -qiE 'EPUBLISHCONFLICT|cannot publish over|already present|409' "$WORK/pub.err"; then
    log "test_library already present on registry — ok"
  else
    cat "$WORK/pub.err"; exit 1
  fi
fi
