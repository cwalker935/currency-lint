import unittest

from currencylint.linter import check_line, lint_stream


def findings_for(line: str):
    return list(check_line(line, 1))


class BareNumbersTests(unittest.TestCase):
    def test_bare_number_without_currency_is_ignored(self):
        # no symbol or ISO code nearby -- nothing to anchor the check to
        self.assertEqual(findings_for("Just a number: 42.999"), [])


class DecimalPrecisionTests(unittest.TestCase):
    def test_two_decimal_currency_with_correct_precision(self):
        self.assertEqual(findings_for("Total due: USD 19.99"), [])

    def test_two_decimal_currency_with_wrong_precision(self):
        line = "Total due: USD 19.999"
        findings = findings_for(line)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.rule, "bad-decimal-precision")
        self.assertEqual(finding.column, line.index("19.999") + 1)
        self.assertIn("2 decimal digit(s)", finding.message)
        self.assertIn("found 3", finding.message)

    def test_zero_decimal_currency_with_no_fraction_is_fine(self):
        self.assertEqual(findings_for("JPY 500"), [])

    def test_zero_decimal_currency_with_fraction_is_flagged(self):
        findings = findings_for("Legacy price: JPY 500.00")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "bad-decimal-precision")
        self.assertIn("0 decimal digit(s)", findings[0].message)
        self.assertIn("found 2", findings[0].message)

    def test_three_decimal_currency_with_correct_precision(self):
        self.assertEqual(findings_for("BHD 12.345"), [])

    def test_three_decimal_currency_with_wrong_precision(self):
        findings = findings_for("BHD 12.34")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "bad-decimal-precision")
        self.assertIn("3 decimal digit(s)", findings[0].message)

    def test_currency_symbol_resolves_to_its_iso_code_rules(self):
        # yen sign should follow JPY's zero-decimal expectation, not the 2-digit default
        findings = findings_for("¥500.00")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "bad-decimal-precision")
        self.assertIn("0 decimal digit(s)", findings[0].message)


class SeparatorTests(unittest.TestCase):
    def test_us_style_thousands_and_decimal_separators(self):
        self.assertEqual(findings_for("USD 1,234.56"), [])

    def test_euro_style_thousands_and_decimal_separators(self):
        self.assertEqual(findings_for("EUR 1.234,56"), [])

    def test_repeated_decimal_separator_is_malformed(self):
        line = "Invoice: 12.34.56 USD"
        findings = findings_for(line)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "malformed-amount")

    def test_inconsistent_thousands_grouping_is_malformed(self):
        findings = findings_for("USD 12,34.56")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "malformed-amount")

    def test_malformed_amount_suppresses_precision_check(self):
        # a malformed amount has no reliable fraction to check precision against
        findings = findings_for("USD 12.34.56")
        self.assertEqual([f.rule for f in findings], ["malformed-amount"])


class TrailingSignTests(unittest.TestCase):
    def test_trailing_sign_is_flagged(self):
        findings = findings_for("Refund: $42.50-")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "trailing-sign")

    def test_leading_sign_is_not_flagged(self):
        self.assertEqual(findings_for("Refund: -42.50 USD"), [])


class MultipleAmountsTests(unittest.TestCase):
    def test_each_amount_on_a_line_is_checked_independently(self):
        line = "Prices: USD 19.999 and JPY 500.00"
        findings = findings_for(line)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].rule, "bad-decimal-precision")
        self.assertEqual(findings[0].column, line.index("19.999") + 1)
        self.assertEqual(findings[1].rule, "bad-decimal-precision")
        self.assertEqual(findings[1].column, line.index("500.00") + 1)


class LintStreamTests(unittest.TestCase):
    def test_line_numbers_follow_the_input(self):
        lines = [
            "clean line, nothing to see\n",
            "Total due: USD 19.999\n",
            "another clean line\n",
            "Refund: $42.50-\n",
        ]
        findings = list(lint_stream(lines))
        self.assertEqual([f.line for f in findings], [2, 4])

    def test_empty_stream_yields_nothing(self):
        self.assertEqual(list(lint_stream([])), [])


if __name__ == "__main__":
    unittest.main()
