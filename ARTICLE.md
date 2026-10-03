# I Installed One Innocent Package. It Read My Secrets Before My Code Ran.

*A hands-on supply-chain attack lab you can run on a laptop in five minutes — built to prove how bad it gets, and engineered to stop one step short of being a weapon.*

---

## The uncomfortable truth about `npm install` and `pip install`

Every time you install a dependency, you are running a stranger's code **as you**, on your machine, *before your own program ever starts*. Not when you import the library. Not when you call a function. At **install time**.

Most developers picture a dependency as code that sits quietly until called. The reality is that package managers hand a brand-new, untrusted package a free execution slot during installation — npm's `postinstall` lifecycle script, Python's `setup.py` — and that slot runs with your user's privileges, your environment variables, and your network access.

This isn't theoretical. It's how `event-stream` (2018) stole Bitcoin wallets, how `ua-parser-js` (2021) shipped a cryptominer and credential stealer to millions, how `codecov` leaked CI secrets across thousands of repos, and how a steady drip of PyPI typosquats keeps exfiltrating cloud tokens today.

I wanted to *feel* how fast and how quietly this happens. So I built a lab — a mock CI build agent pulling one dependency from an internal registry, on my own machine — and ran it. Here's exactly what came back.

---

## The lab, in one diagram

```
  victim (pip install)          the "collector"
  ┌────────────────────┐        ┌────────────────────┐
  │ wants: awesome-utils│  TCP   │ listens on :4444   │
  │ a normal string lib │ ─────► │ logs whatever lands│
  └────────────────────┘ beacon └────────────────────┘
         ▲
         │ install hook fires here — BEFORE any import
```

`awesome-utils` is a **real, working** library. It genuinely does what it advertises:

```python
awesome_utils.shout("build complete")   # -> 'BUILD COMPLETE!'
awesome_utils.slugify("Supply Chain Lab")  # -> 'supply-chain-lab'
```

That's the point. A malicious package doesn't look malicious. It works. You keep it. The teeth are in the *install hook*, not the runtime code — which is why reading a library's source and thinking "looks fine" doesn't save you.

---

## Running it against a real CI build agent

The whole thing is three containers — a collector, an internal package registry
serving the poisoned `awesome-utils`, and an unprivileged CI build agent that
installs it:

```
$ docker compose up --build
```

The collector comes up first:

```
sc-attacker | [collector] listening on 0.0.0.0:4444 for install-time beacons...
```

The victim is a containerized CI build agent — an **unprivileged** `ci` user, a
deploy secret in its environment like every CI system on earth, pulling the
dependency **by name** from an internal package index. Exactly what a build runs:

```
$ pip install --user --index-url http://registry:8080/simple/ awesome-utils
Looking in indexes: http://registry:8080/simple/
...
Successfully installed awesome-utils-1.3.7
$ python -c "import awesome_utils; print(awesome_utils.shout('build complete'))"
BUILD COMPLETE!          # <- build is green. Nothing looks wrong.
```

The install succeeded. The library imports and works. A developer sees nothing.

Meanwhile, back on the collector (a different container the build never meant to talk to):

```
============================================================
[12:21:33] BEACON from 172.21.0.4:53682
============================================================
=== SUPPLY-CHAIN LAB BEACON ===
event:    awesome-utils install hook fired
time:     2026-10-03T12:21:33.238955Z
host:     6e4d6c3f1adb
user:     ci
platform: Linux-6.10.14-linuxkit-aarch64-with-glibc2.41
cwd:      /tmp/pip-install-l_fvgez8/awesome-utils_5f9b9130e6204a59bc3f142bbf41f3e4
loot:     CI_DEPLOY_TOKEN=prod-deploy-key-8f3a9c2e-DO-NOT-LEAK
exec:     `id` -> uid=1000(ci) gid=1000(ci) groups=1000(ci)
```

Read that again. In the time it took `pip` to print nothing alarming, the package:

1. **Ran arbitrary OS commands** as the build's own `ci` user — the `id` output is live proof, not a simulation. Note it is **not root**: this needs no privilege, because the thing it steals is just sitting in the environment.
2. **Read the build environment** and **exfiltrated a production deploy token** to a host the build agent never meant to contact.
3. Did it **before a single line of the app ran**, and left the build looking perfectly healthy.

No exploit. No CVE. No vulnerability in the classic sense. Just a package manager doing exactly what it's designed to do, for a package that chose to abuse it.

---

## The detail that surprised me: wheels silently change the game

My first version hid the payload in `setup.py`'s `install` command hook — the "textbook" spot. **It never fired.**

Modern pip (PEP 517) builds a **wheel** and installs *that*. A wheel is a pre-built archive with no build step, so `setup.py install` is never executed. A payload hidden only in the install command is **dead code** against a modern toolchain.

Real-world PyPI malware knows this. It puts the payload at the **top level of `setup.py`**, which runs during the *wheel build* itself:

```python
# runs every time setup.py is executed — including the PEP 517 build step
if os.environ.get("_LAB_BEACON_FIRED") != "1":
    _beacon()
```

Move it there and it fires every time — as the capture above shows. This cuts both ways, and it's the most useful defensive takeaway in the whole lab: **prefer pre-built wheels, and be very suspicious of any package that forces a source build.** (More on that below.)

---

## The scariest part isn't a reverse shell

If you've seen one of these demos, you expect it to end with a shell popping open on the attacker's screen. I deliberately **did not** build that, and here's the thing I didn't appreciate until I ran the numbers: **a reverse shell is the *least* likely outcome in a real supply-chain attack.**

A shell is loud, interactive, and needs the operator sitting there. Real compromises do the quiet, non-interactive things — all of which my beacon *already demonstrated it could do*:

- **Steal secrets and tokens** — done, above. Your CI token is the crown jewel.
- **Drop persistence** — a cron job, a systemd unit, a line in `~/.bashrc`, a second hook.
- **Worm into other packages** — poison the lockfile, publish to internal registries.
- **Exfiltrate source, SSH keys, cloud credentials.**

None of those need an interactive shell. The damage is done at install time, silently, and it's usually finished before anyone could type a command into a shell anyway. That reframing — *the beacon is already the whole attack* — is the point I most wanted this lab to make.

---

## Where I stopped, and why

This lab proves capability and then **refuses to weaponize it**. Every payload:

- sends **one** context beacon and exits;
- runs **one fixed, harmless command** (`id`) to prove execution — no attacker input, no command channel;
- ships **no shell, no persistence, no worming, no input channel** — nothing an attacker could lift and point at a victim.

The beacon literally prints the line *"An interactive reverse shell is possible but loud. This lab STOPS HERE."* The educational value lives entirely in the **vector** (install-time execution reaching your secrets), not in a turnkey implant. Everything runs on an isolated Docker bridge (or your own loopback) that you control. Don't publish `awesome-utils` anywhere. Don't point it at anyone.

---

## How to actually defend against this

The lab ships a detection + mitigation track. The short version:

**Stop the hooks from running**
- npm: `npm install --ignore-scripts` (and set it in `.npmrc` org-wide). This single flag neuters the entire lifecycle-script class.
- pip: **prefer wheels** (`--only-binary :all:` where feasible); treat a forced source build as a red flag.

**Shrink the blast radius**
- Pin versions **and** hashes (`package-lock.json`, `pip install --require-hashes`).
- Scope private names to your private registry so a public typosquat can't outrank them — the fix for dependency-confusion.
- Don't put long-lived secrets in build environments. Use short-lived, scoped tokens (OIDC), so a leaked `CI_DEPLOY_TOKEN` is worth little.

**Catch it when it runs**
- Watch build-agent egress. A `node` or `python` process opening an outbound socket *during install* is the signature. On a box: `lsof -nP -i` / `ss -tnp` filtered to the install window.
- Alert on install steps that make network connections at all — most legitimate installs don't need to.

---

## Try it yourself

The full lab — npm and pip payloads, a Dockerized internal-registry scenario, a dependency-confusion walkthrough, and the detection scripts — is laid out so you can run every piece in minutes. Stand up the collector, install the package, watch your own secrets walk out the door, then turn on `--ignore-scripts` / wheels and watch it go quiet.

Nothing teaches "pin your dependencies" like watching a deploy token you typed ten seconds ago show up on a machine across the room.

*Lab-only. Built for defenders. Point it at nothing but yourself.*
