"""
deploy-api :: a real token service for the supply-chain lab.

Mints and verifies REAL HS256 JWTs (hand-rolled from hmac/hashlib so the
signature check is genuine, not a string compare). Two endpoints:

  GET  /token    -> issues a short-lived deploy JWT for the `ci` principal.
                    Stand-in for the OIDC / secrets-store handoff a real CI
                    pipeline uses to obtain a deploy credential at build start.
  POST /deploy   -> requires `Authorization: Bearer <jwt>`. Verifies the
                    signature, expiry, and scope. 200 on a valid token,
                    403 on missing / forged / expired / wrong-scope.

The signing secret never leaves this service. The attacker cannot forge a
token — but a *stolen valid* token works, which is the whole point.

Lab-only. Binds inside the isolated Docker network.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Secret lives only in this container. Generated at startup so it is never a
# constant baked into the repo.
SECRET = os.environ.get("DEPLOY_SIGNING_SECRET") or base64.b64encode(os.urandom(32)).decode()
ISSUER = "deploy-api.lab"
TOKEN_TTL = 900  # seconds


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint(sub: str, scope: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "sub": sub,
        "scope": scope,
        "iat": now,
        "exp": now + TOKEN_TTL,
        "jti": _b64url(os.urandom(8)),
    }
    signing_input = _b64url(json.dumps(header, separators=(",", ":")).encode()) + "." + \
        _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    return signing_input + "." + _b64url(sig)


def verify(token: str):
    """Return (ok, reason, claims). Real signature + expiry + scope checks."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        return False, "malformed", None
    signing_input = header_b64 + "." + payload_b64
    expected = hmac.new(SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    # constant-time compare -> tampered signatures fail here
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        return False, "bad signature", None
    try:
        claims = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return False, "bad payload", None
    if claims.get("exp", 0) < int(time.time()):
        return False, "expired", claims
    if claims.get("scope") != "deploy":
        return False, "insufficient scope", claims
    return True, "ok", claims


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[deploy-api] " + (fmt % args), flush=True)

    def do_GET(self):
        if self.path.rstrip("/") == "/token":
            tok = mint(sub="ci", scope="deploy")
            print("[deploy-api] issued deploy token for sub=ci (exp in "
                  f"{TOKEN_TTL}s)", flush=True)
            self._send(200, {"token": tok, "token_type": "Bearer", "expires_in": TOKEN_TTL})
        elif self.path.rstrip("/") in ("", "/health"):
            self._send(200, {"status": "ok", "issuer": ISSUER})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/deploy":
            self._send(404, {"error": "not found"})
            return
        auth = self.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        src = self.client_address[0]
        if not token:
            print(f"[deploy-api] DENY  deploy from {src}: no token -> 403", flush=True)
            self._send(403, {"error": "missing bearer token"})
            return
        ok, reason, claims = verify(token)
        if not ok:
            print(f"[deploy-api] DENY  deploy from {src}: {reason} -> 403", flush=True)
            self._send(403, {"error": reason})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b"{}"
        try:
            app = json.loads(body or b"{}").get("app", "unknown-app")
        except Exception:
            app = "unknown-app"
        release = "rel-" + _b64url(os.urandom(4))
        print(f"[deploy-api] ALLOW deploy from {src} as sub={claims['sub']} "
              f"scope={claims['scope']} -> 200 ({release})", flush=True)
        self._send(200, {
            "status": "deployed",
            "deployed_as": claims["sub"],
            "app": app,
            "release": release,
            "note": "A valid deploy token was presented. In production this would "
                    "ship code to the victim's environment.",
        })


def main():
    port = int(os.environ.get("PORT", "9000"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[deploy-api] listening on 0.0.0.0:{port} — issuer={ISSUER}, HS256, "
          f"TTL={TOKEN_TTL}s", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
