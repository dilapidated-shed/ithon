import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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

    def test_multiline_typed_function_header(self):
        source = (
            "def determinant(\n"
            "    p_x ∈ float,\n"
            "    p_y ∈ float,\n"
            "    q_x ∈ float,\n"
            "    q_y ∈ float,\n"
            ") → float:\n"
            "    return p_x × q_y - p_y × q_x\n"
            "area ∈ float ← determinant(1.0, 2.0, 3.0, 4.0)\n"
        )
        lowered = lower_source(source)
        self.assertEqual(lowered.count("\n"), source.count("\n"))
        self.assertIn("    p_x: float,", lowered)
        self.assertIn(") -> float:", lowered)
        check_source(source)

    def test_successful_check_writes_content_addressed_receipt(self):
        source = "answer ∈ int ← 6 × 7\n"
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "checked.jsonl"
            with patch.dict(os.environ, {"ITHON_CHECK_RECEIPT": str(receipt)}):
                check_source(source, "answer.pi")
            record = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(record["schema"], "ithon.checked.v1")
        self.assertEqual(record["filename"], "answer.pi")
        self.assertEqual(
            record["source_sha256"],
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
        )

    def test_failed_check_does_not_write_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "checked.jsonl"
            with patch.dict(os.environ, {"ITHON_CHECK_RECEIPT": str(receipt)}):
                with self.assertRaises(StaticTypeError):
                    check_source("answer ∈ int ← 'wrong'\n", "wrong.pi")
            self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
