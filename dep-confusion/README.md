# Dependency-confusion scenario (lab walkthrough)

The torchtriton / Alex Birsan class: a project references an **internal** package
name that isn't on the public registry. An attacker publishes that same name
publicly with a higher version; the installer prefers the public one and pulls the
attacker's code — which runs its install hook. No typo, no compromise of the real
package required.

## Simulate it locally (no public registry needed)

1. Victim's manifest references an "internal" name:
   `victim-app/package.json` → `"@acme-internal/logging": "^1.0.0"`

2. Two registries resolve that name:
   - **private** (intended): version `1.0.4`
   - **public** (attacker): version `99.0.0`  ← higher version wins

3. With a naive `npm install` (no scoped-registry pinning), the resolver takes
   `99.0.0`, whose `postinstall` beacons — reuse `evil-utils/postinstall.js`.

## The defense to demonstrate
Pin the scope to the private registry so the public name can never resolve:
```
# .npmrc
@acme-internal:registry=https://registry.internal.acme.example/
```
Python equivalent: `--index-url` for the private index + `--no-index` for the
confused name, or an explicit allow-list. Show that with the scope pinned, the
`99.0.0` public package is never even queried.

## What to capture
- resolver output showing which version/registry won (`npm install --loglevel=silly | grep <name>`)
- the beacon landing on your listener when confusion succeeds
- no beacon after the `.npmrc` scope pin — that's the mitigation proof
