#!/usr/bin/env python3
"""Render a Happ deeplink as a PNG QR code."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="text file containing a deeplink")
    parser.add_argument("destination", help="output PNG path")
    args = parser.parse_args()

    deeplink = Path(args.source).read_text(encoding="utf-8").strip()
    if not deeplink.startswith("happ://routing/"):
        raise SystemExit("source does not contain a Happ routing deeplink")

    try:
        import qrcode
    except ImportError as exc:
        raise SystemExit("install CI dependencies: pip install -r requirements-ci.txt") from exc

    destination = Path(args.destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    qrcode.make(deeplink).save(destination)
    print(f"QR: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
