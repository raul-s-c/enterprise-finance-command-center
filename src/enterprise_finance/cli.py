from __future__ import annotations

import argparse
from datetime import date

from .engine import build


def previous_month() -> str:
    today = date.today()
    year = today.year
    month = today.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}-{month:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Enterprise Finance Command Center dataset")
    parser.add_argument("build", nargs="?")
    parser.add_argument("--end-month", default=previous_month())
    args = parser.parse_args()
    result = build(args.end_month)
    print(result)


if __name__ == "__main__":
    main()
