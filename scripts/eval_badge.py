#!/usr/bin/env python3
"""Write docs/badges/eval.svg from a pytest JSON report (OBS-03)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def badge_svg(*, passed: int, total: int) -> str:
    rate = 100 if total == 0 else round(100 * passed / total)
    label = "evals"
    value = f"{passed}/{total} ({rate}%)"
    color = "#4c1" if rate >= 90 else "#dfb317" if rate >= 70 else "#e05d44"
    label_w = 44
    value_w = 8 * len(value) + 20
    width = label_w + value_w
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{label}: {value}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="m"><rect width="{width}" height="20" rx="3" fill="#fff"/></mask>
  <g mask="url(#m)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
    <rect width="{width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_w / 2}" y="15">{label}</text>
    <text x="{label_w + value_w / 2}" y="15">{value}</text>
  </g>
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True, help="pytest --json-report output")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/badges/eval.svg"),
        help="SVG destination",
    )
    args = parser.parse_args()
    data = json.loads(args.report.read_text(encoding="utf-8"))
    summary = data.get("summary") or {}
    passed = int(summary.get("passed", 0))
    total = int(summary.get("total", passed))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(badge_svg(passed=passed, total=total), encoding="utf-8")
    print(f"Wrote {args.out} ({passed}/{total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
