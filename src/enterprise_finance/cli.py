from __future__ import annotations

import argparse
from datetime import date

from .engine_v15 import build


def previous_month() -> str:
    today = date.today()
    year, month = today.year, today.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}-{month:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Enterprise Finance Command Center dataset")
    parser.add_argument("build", nargs="?")
    parser.add_argument("--end-month", default=previous_month())
    parser.add_argument("--offline-macro", action="store_true", help="Disable live ECB FX retrieval")
    args = parser.parse_args()
    result = build(args.end_month, allow_live_macro=not args.offline_macro)
    print(result)


if __name__ == "__main__":
    main()
