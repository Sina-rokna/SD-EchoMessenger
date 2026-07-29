#!/usr/bin/env python
"""Wait for a TCP dependency without requiring netcat in the image."""

from __future__ import annotations

import socket
import sys
import time


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print("usage: wait-for-service.py HOST PORT [NAME]", file=sys.stderr)
        return 2

    host = sys.argv[1]
    port = int(sys.argv[2])
    name = sys.argv[3] if len(sys.argv) == 4 else f"{host}:{port}"
    deadline = time.monotonic() + 60

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"{name} is reachable.")
                return 0
        except OSError:
            time.sleep(1)

    print(f"Timed out waiting for {name}.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
