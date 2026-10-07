# Supply-Chain Research Lab

Studies the core supply-chain primitive: **a dependency runs code at install time,
before any import.** Every payload here is a **dummy beacon** — a one-shot context
check-in (host, user, and any CI secrets it can read) to a lab collector, then it
exits. No shell, no command channel, no persistence.

## Three ways to run it

### A. Dockerized end-to-end (most realistic)
A "real" package (`malicious-pkg/awesome-utils` — genuinely working helpers) is
served from an internal registry and installed by a victim CI build agent. The
install hook beacons the build's `CI_DEPLOY_TOKEN` to the collector.
```
docker compose up --build
```
Watch `sc-attacker` print the beacon with the leaked token. The victim build
still goes green — that's the point.

### B. npm, local (internal registry)
The victim pulls a **version range** (`test_library@^1.0.0`) from a lab-only
registry — the realistic path, not a `file:` shortcut. Boot the registry and
publish the poisoned package first, then install:
```
sh registry-npm/publish.sh            # boots Verdaccio on :4873, publishes test_library
cd victim-app && npm install          # resolves ^1.0.0 from :4873, postinstall beacons
```
`victim-app/.npmrc` points npm at `http://127.0.0.1:4873/`. The registry is
offline and bound to localhost; nothing is ever published to public npm.

Catch the check-in with a collector on :4444 first — simplest is
`ncat -lvnkp 4444`. (`attacker/listener.py` is the fuller collector that also
*replays* the stolen token, but it needs `deploy-api` running, so that's the
Docker/CI chain in scenario A, not local B.) `publish.sh` leaves Verdaccio
running in the background; stop it with `pkill -f verdaccio` when you're done.

### C. pip, local
```
cd pip-victim && pip install -r requirements.txt   # setup.py hook beacons
```
(Run from inside `pip-victim/` — the requirement path `../pip-evil` is resolved
relative to your current directory, not to the requirements file.)
Point any local payload at your VM: `LAB_HOST=10.37.129.50 LAB_PORT=4444 ...`

## Layout
- `malicious-pkg/` — the "real" dependency (works as advertised) + beacon install hook
- `test_library/`  — npm equivalent (`postinstall`), served from the internal registry
- `registry-npm/`  — lab Verdaccio config + `publish.sh` that boots it and publishes `test_library`
- `victim-app/`    — innocent npm app; `.npmrc` + `^1.0.0` pull the poisoned lib from the registry
- `pip-evil/`      — standalone pip equivalent (`setup.py`)
- `attacker/`      — beacon collector (`ncat -lvnkp 4444` works too)
- `registry/`, `victim/` — internal registry + CI victim for the Docker scenario
- `dep-confusion/` — dependency-confusion walkthrough (the torchtriton class)
- `detect/`        — attacker-side capture + defender-side detection

## The lessons
1. Install hooks (`postinstall`, `setup.py`) run before your app does.
2. That code already sees your build secrets — the beacon proves it by leaking the token.
3. Reading a package's *runtime* source doesn't clear it; the hook lives in the manifest.
4. Defenses: `--ignore-scripts`, prefer wheels, pin hashes/lockfiles, scope-pin private
   registries (kills dependency confusion), watch build-agent egress (`detect/`).

## Scope
Lab-only, points at your own VM / isolated Docker net. Payloads beacon once and exit.
