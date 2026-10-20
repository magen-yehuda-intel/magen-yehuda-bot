#!/usr/bin/env python3
"""Retired one-off countdown. Kept as a safe no-op for old scheduler entries.

The original deadline has passed. A historical event must not be rebroadcast
as a live alert. This entry point deliberately reads no secrets and sends no
network requests. Future deadlines require sourced data and an expiry policy.
"""
import sys


def main():
    print("Retired countdown: no alert sent.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
