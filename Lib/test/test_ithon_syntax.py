import ast
import token
import tokenize
import unittest
from io import BytesIO

from ithon_frontend import lower_source


class UnicodeSyntaxTests(unittest.TestCase):
    def run_source(self, source):
        namespace = {}
        exec(lower_source(source), namespace)
        return namespace

    def test_left_assignment(self):
        ns = self.run_source("x ← 40 + 2")
        self.assertEqual(ns["x"], 42)

    def test_left_assignment_chain(self):
        ns = self.run_source("x ← y ← 42")
        self.assertEqual((ns["x"], ns["y"]), (42, 42))

    def test_right_assignment(self):
        ns = self.run_source("40 + 2 → x")
        self.assertEqual(ns["x"], 42)

    def test_right_assignment_chain(self):
        ns = self.run_source("42 → x → y")
        self.assertEqual((ns["x"], ns["y"]), (42, 42))

    def test_typed_membership_assignment(self):
        for source in (
            "x ∈ int ← 42",
            "int ∋ x ← 42",
            "42 → x ∈ int",
            "42 → int ∋ x",
        ):
            with self.subTest(source=source):
                lowered = lower_source(source)
                ns = {}
                exec(lowered, ns)
                self.assertEqual(ns["x"], 42)
                tree = ast.parse(lowered)
                self.assertIsInstance(tree.body[0], ast.AnnAssign)
                self.assertEqual(tree.body[0].target.id, "x")

    def test_unicode_arithmetic(self):
        self.assertEqual(eval(lower_source("6 × 7")), 42)
        self.assertEqual(eval(lower_source("6 • 7")), 42)
        self.assertEqual(eval(lower_source("6 · 7")), 42)
        self.assertEqual(eval(lower_source("84 ÷ 2")), 42)

    def test_unicode_lambda_spellings(self):
        ns = self.run_source(
            "double ← λ x: x × 2\n"
            "triple ← ƒ x: x × 3\n"
        )
        self.assertEqual(ns["double"](21), 42)
        self.assertEqual(ns["triple"](14), 42)

    def test_lambda_glyphs_remain_identifiers_elsewhere(self):
        ns = self.run_source("λ ← 20\nƒ ← 22\nanswer ← λ + ƒ")
        self.assertEqual(ns["answer"], 42)

    def test_unicode_operators_do_not_require_spaces(self):
        ns = self.run_source(
            "x←6×7\n"
            "42→y\n"
            "a←6\n"
            "b←7\n"
            "z←a·b\n"
            "λ←42\n"
            "λ→q\n"
        )
        self.assertEqual(
            (ns["x"], ns["y"], ns["z"], ns["q"]),
            (42, 42, 42, 42),
        )

    def test_unicode_multiplication_is_not_unpacking(self):
        with self.assertRaises(SyntaxError):
            compile(lower_source("f(×xs)"), "<test>", "exec")

    @unittest.skipUnless(hasattr(token, "LEFT_ASSIGN"), "requires native Ithon tokenizer")
    def test_exact_token_types(self):
        expected = {
            "←": token.LEFT_ASSIGN,
            "→": token.RIGHT_ASSIGN,
            "÷": token.DIVIDE,
            "×": token.TIMES,
            "•": token.BULLET,
            "·": token.MIDDOT,
        }
        source = "x ← 6 × 7\n42 → y\n84 ÷ 2\n6 • 7\n6 · 7\n"
        tokens = tokenize.tokenize(BytesIO(source.encode()).readline)
        actual = {
            tok.string: tok.exact_type
            for tok in tokens
            if tok.string in expected
        }
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
