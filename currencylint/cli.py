from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from .linter import Finding, lint_stream


def _print_text(path: str, finding: Finding) -> None:
    print(f"{path}:{finding}")


def _print_json(path: str, finding: Finding) -> None:
    record = {
        "path": path,
        "line": finding.line,
        "column": finding.column,
        "rule": finding.rule,
        "message": finding.message,
        "text": finding.text,
    }
    # one JSON object per line rather than a top-level array, so output can
    # still be streamed and consumed before the whole input has been read
    print(json.dumps(record))


def _lint_path(path: str, emit) -> int:
    count = 0
    display_path = "<stdin>" if path == "-" else path
    handle = sys.stdin if path == "-" else open(path, encoding="utf-8")
    try:
        for finding in lint_stream(handle):
            emit(display_path, finding)
            count += 1
    finally:
        if handle is not sys.stdin:
            handle.close()
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
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="output format: human-readable text (default) or newline-delimited JSON",
    )
    args = parser.parse_args(argv)

    emit = _print_json if args.format == "json" else _print_text
    total = sum(_lint_path(path, emit) for path in args.paths)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
