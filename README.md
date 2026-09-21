# currencylint

A small linter for currency amounts in text files -- invoice exports, log
lines, CSV dumps, whatever. It flags amounts that are ambiguous or wrong in
ways that tend to cause real money bugs: a fraction with the wrong number of
decimal digits for its currency, a sign that trails the number instead of
leading it, or thousands/decimal separators that don't agree with each other.

It reports one finding per problem, with a line number, so you can point it
at a file and go straight to the offending line.

## Why

Currency amounts in free-form text come from a lot of places -- hand-typed
invoices, exports from systems that assume a locale, copy-pasted numbers --
and small formatting mistakes are easy to miss by eye and easy to get wrong
downstream (rounding a three-decimal fraction to two, parsing "1.234,56" as
1.234 instead of 1234.56, missing a minus sign because it's at the end of the
token). This tool doesn't try to reformat anything; it just tells you where
to look.

## Usage

```
$ cat prices.txt
Total due: USD 19.999
Refund: $42.50-
Legacy price: JPY 500.00
Invoice: 12.34.56 USD

$ currencylint prices.txt
prices.txt:1:16: bad-decimal-precision: USD amounts should have 2 decimal digit(s), found 3 ('USD 19.999')
prices.txt:2:10: trailing-sign: negative sign trails the amount instead of leading it ('$42.50-')
prices.txt:3:19: bad-decimal-precision: JPY amounts should have 0 decimal digit(s), found 2 ('JPY 500.00')
prices.txt:4:10: malformed-amount: inconsistent thousands/decimal separators ('12.34.56 USD')
```

Exit status is 1 if anything was flagged, 0 otherwise -- suitable for a CI
check. Pass one or more file paths, or omit them (or pass `-`) to read from
stdin.

```
$ tail -f transactions.log | currencylint
```

## Streaming

`currencylint` never reads a whole file into memory. `lint_stream()` takes
any iterable of lines -- a file object, `sys.stdin` -- and processes them one
at a time, so it's safe to run over logs far larger than available RAM or
over a pipe that never ends.

```python
from currencylint import lint_stream

with open("huge_export.csv", encoding="utf-8") as f:
    for finding in lint_stream(f):
        print(finding)
```

## Rules

- `bad-decimal-precision` -- the fractional part doesn't match what the
  currency expects (2 digits for most currencies, 0 for JPY/KRW/VND, 3 for
  BHD/KWD/OMR).
- `trailing-sign` -- a minus sign appears after the digits (`42.50-`) rather
  than before them.
- `malformed-amount` -- thousands and decimal separators are used
  inconsistently within one number, so it's not clear what the value is.

An amount is only checked when a currency symbol (`$ € £ ¥`) or a known ISO
code (USD, EUR, JPY, ...) sits right next to the number. Bare numbers are
left alone.

## Install

No dependencies beyond the standard library.

```
pip install -e .
```

## Tests

```
python -m unittest discover
```

## License

MIT, see [LICENSE](LICENSE).
