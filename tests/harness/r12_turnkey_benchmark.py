#!/usr/bin/env python3
"""Canonical R12 turnkey benchmark entrypoint."""

from __future__ import annotations

import sys

from pyocd_debug_mcp.brain.cli import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(["benchmark", *sys.argv[1:]]))
