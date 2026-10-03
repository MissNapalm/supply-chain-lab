# Detecting the install-time beacon

The whole attack happens during `npm install`, so detection lives there.

## 1. See the connection from the attacker side
On the VM listener, catch the check-in:
```
ncat -lvnkp 4444      # -k keeps it open for repeated installs
```
You'll see the beacon block with victim hostname/user/cwd each install.

## 2. Spot lifecycle scripts BEFORE installing (the real defense)
```
npm install --ignore-scripts          # install without running hooks
npm ls --all                          # what's actually in the tree
cat node_modules/*/package.json | grep -A1 '"scripts"'   # hunt pre/post hooks
```
`--ignore-scripts` is the single biggest mitigation — it neuters this entire class.

## 3. Catch it on the host at runtime
```
# macOS: watch for node spawning outbound connections during install
sudo lsof -i -P | grep -i node
# Linux lab victim:
sudo ss -tnp | grep node
```
Correlate: a `node` process opening a socket to :4444 whose parent is `npm`/lifecycle
is the signature.

## 4. Supply-chain hygiene to study
- lockfile pinning + integrity hashes (`package-lock.json`)
- `npm audit signatures` / provenance
- dependency-confusion: internal name published to public registry (the torchtriton case)
- typosquats: `expresss`, `lodahs`, etc.
