from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .linter import lint_stream


def _lint_path(path: str) -> int:
    count = 0
    if path == "-":
        for finding in lint_stream(sys.stdin):
            print(f"<stdin>:{finding}")
            count += 1
        return count

    with open(path, encoding="utf-8") as handle:
        for finding in lint_stream(handle):
            print(f"{path}:{finding}")
            count += 1
    return count


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="currencylint",
        description="Flag suspicious currency amount formatting, line by line.",
    )
    parser.add_argument(
        "paths", nargs="*", default=["-"],
        help='files to check (reads stdin if omitted or "-")',
    )
    args = parser.parse_args(argv)

    total = sum(_lint_path(path) for path in args.paths)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
