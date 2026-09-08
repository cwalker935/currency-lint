"""Rules for spotting badly formatted currency amounts, one line at a time."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}

# Deliberately a short, known list rather than "any three uppercase letters" --
# that would turn every stray acronym in a log line into a false positive.
ISO_CODES = [
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR", "KRW",
    "VND", "BHD", "KWD", "OMR", "MXN", "BRL", "ZAR", "SEK", "NOK", "DKK",
    "PLN", "RUB", "TRY", "SGD", "HKD", "NZD",
]

ZERO_DECIMAL_CODES = {"JPY", "KRW", "VND"}
THREE_DECIMAL_CODES = {"BHD", "KWD", "OMR"}

_SYMBOL_CLASS = "".join(re.escape(s) for s in CURRENCY_SYMBOLS)
_CODE_ALTERNATION = "|".join(sorted(ISO_CODES, key=len, reverse=True))

# A "number" is deliberately permissive here (digits plus . and ,) -- the
# separator analysis in _split_number is what decides if it's well formed.
AMOUNT_RE = re.compile(
    rf"(?P<pre_sym>[{_SYMBOL_CLASS}])?\s*"
    rf"(?P<pre_code>\b(?:{_CODE_ALTERNATION})\b)?\s?"
    r"(?P<number>\d(?:[\d,.]*\d)?)"
    r"(?P<sign>-)?"
    rf"\s?(?P<post_sym>[{_SYMBOL_CLASS}])?"
    rf"(?:\s?(?P<post_code>\b(?:{_CODE_ALTERNATION})\b))?"
)


@dataclass(frozen=True)
class Finding:
    line: int
    column: int
    rule: str
    message: str
    text: str

    def __str__(self) -> str:
        return f"{self.line}:{self.column}: {self.rule}: {self.message} ({self.text!r})"


def _resolve_code(match: "re.Match[str]") -> Optional[str]:
    code = match.group("pre_code") or match.group("post_code")
    if code:
        return code
    symbol = match.group("pre_sym") or match.group("post_sym")
    if symbol:
        return CURRENCY_SYMBOLS.get(symbol)
    return None


def _split_number(number: str) -> tuple[Optional[str], bool]:
    """Split off the fractional part of a raw number token.

    The last '.' or ',' is treated as the decimal point; anything earlier
    is a thousands separator and must group digits in threes. Returns
    (fraction_or_None, malformed).
    """
    last_pos = max(number.rfind("."), number.rfind(","))
    if last_pos == -1:
        return None, False

    head, fraction = number[:last_pos], number[last_pos + 1:]
    decimal_sep = number[last_pos]
    thousands_sep = "," if decimal_sep == "." else "."

    if thousands_sep in head:
        groups = head.split(thousands_sep)
        malformed = len(groups[0]) > 3 or any(len(g) != 3 for g in groups[1:])
    elif decimal_sep in head:
        # the decimal separator itself repeats, e.g. "12.34.56"
        malformed = True
    else:
        malformed = False

    return fraction, malformed


def check_line(line: str, lineno: int) -> Iterator[Finding]:
    """Yield findings for a single line of text."""
    for match in AMOUNT_RE.finditer(line):
        code = _resolve_code(match)
        if code is None:
            continue  # just a bare number, nothing currency-shaped nearby

        number = match.group("number")
        column = match.start("number") + 1
        text = match.group(0).strip()
        fraction, malformed = _split_number(number)

        if malformed:
            yield Finding(
                lineno, column, "malformed-amount",
                "inconsistent thousands/decimal separators", text,
            )
            continue

        if match.group("sign"):
            yield Finding(
                lineno, column, "trailing-sign",
                "negative sign trails the amount instead of leading it", text,
            )

        if fraction is not None:
            if code in ZERO_DECIMAL_CODES:
                expected = 0
            elif code in THREE_DECIMAL_CODES:
                expected = 3
            else:
                expected = 2
            if len(fraction) != expected:
                yield Finding(
                    lineno, column, "bad-decimal-precision",
                    f"{code} amounts should have {expected} decimal digit(s), "
                    f"found {len(fraction)}",
                    text,
                )


def lint_stream(lines: Iterable[str]) -> Iterator[Finding]:
    """Lint an iterable of lines without ever holding the whole input in memory.

    Pass a file object or sys.stdin directly -- both hand back one line at a
    time -- rather than something like f.readlines(), which defeats the point
    on multi-gigabyte logs.
    """
    for lineno, line in enumerate(lines, start=1):
        yield from check_line(line, lineno)
