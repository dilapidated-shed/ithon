import unittest

from ithon_frontend import StaticTypeError, check_source, lower_source


class UnicodeStaticTypingTests(unittest.TestCase):
    def test_left_arrow_assignment_infers_and_preserves_type(self):
        check_source("x ← 42\nx ← 43")
        with self.assertRaisesRegex(StaticTypeError, "expects int, got str"):
            check_source("x ← 42\nx ← 'forty two'")

    def test_membership_typing_is_reversible(self):
        check_source("x ∈ int ← 42")
        check_source("int ∋ x ← 42")
        check_source("42 → x ∈ int")
        check_source("42 → int ∋ x")

    def test_membership_lowers_to_one_ast_typing_relation(self):
        self.assertEqual(lower_source("x ∈ int ← 42"), "x: int = 42")
        self.assertEqual(lower_source("int ∋ x ← 42"), "x: int = 42")

    def test_colon_typing_is_rejected(self):
        with self.assertRaisesRegex(StaticTypeError, "uses ∈ or ∋, not :"):
            check_source("x: int ← 42")

    def test_unicode_lambda_and_multiplication_use_callable_context(self):
        check_source(
            "double ∈ Callable[[int], int] ← λ x: x × 2\n"
            "answer ← double(21)\n"
        )

    def test_multiline_strings_keep_ithon_glyphs_literal(self):
        source = '"""first line\n← × ÷ λ ƒ\nlast line"""\nvalue ← 6 × 7\n'
        lowered = lower_source(source)
        self.assertIn("← × ÷ λ ƒ", lowered)
        self.assertIn("value = 6 * 7", lowered)


if __name__ == "__main__":
    unittest.main()
