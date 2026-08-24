import unittest

from ithon_frontend import StaticTypeError, check_source


class MandatoryStaticTypingTests(unittest.TestCase):
    def check_ok(self, source):
        check_source(source)

    def check_bad(self, source, text):
        with self.assertRaisesRegex(StaticTypeError, text):
            check_source(source)

    def test_assignment_infers_type(self):
        self.check_ok("x ← 40 + 2\nx ← 43")

    def test_assignment_cannot_change_type(self):
        self.check_bad("x ← 42\nx ← 'forty two'", "expects int, got str")

    def test_membership_type_accepts_numeric_widening(self):
        self.check_ok("x ∈ float ← 42")

    def test_reverse_membership_type_is_the_same_binding(self):
        self.check_ok("float ∋ x ← 42")
        self.check_bad("int ∋ x ← 4.2", "expected int, got float")

    def test_right_assignment_keeps_membership_directionality(self):
        self.check_ok("42 → x ∈ float")
        self.check_ok("42 → float ∋ x")

    def test_colon_is_not_ithon_type_syntax(self):
        self.check_bad("x: int ← 42", "uses ∈ or ∋, not :")
        self.check_bad(
            "def f(x: int) → int:\n    return x",
            "uses ∈ or ∋, not :",
        )

    def test_function_parameters_are_typed(self):
        self.check_bad("def f(x) → int:\n    return 1", "parameter 'x' needs a static type")

    def test_function_return_is_typed(self):
        self.check_bad("def f(x ∈ int):\n    return x", "function 'f' needs a return type")

    def test_return_type_is_checked(self):
        self.check_bad("def f(x ∈ int) → int:\n    return 'x'", "expected int, got str")

    def test_local_function_call_is_checked(self):
        self.check_bad(
            "def double(x ∈ int) → int:\n"
            "    return x × 2\n"
            "answer ← double('21')",
            "expected int, got str",
        )

    def test_lambda_requires_callable_context(self):
        self.check_bad("double ← λ x: x × 2", "lambda needs a contextual Callable")

    def test_lambda_uses_callable_context(self):
        self.check_ok("double ∈ Callable[[int], int] ← λ x: x × 2\nanswer ← double(21)")

    def test_external_unknown_result_needs_membership_type(self):
        self.check_bad("import math\nx ← math.sqrt(4.0)", "cannot infer assignment type")
        self.check_ok("import math\nx ∈ float ← math.sqrt(4.0)")

    def test_for_loop_infers_from_range(self):
        self.check_ok("total ← 0\nfor i in range(4):\n    total ← total + i")

    def test_empty_container_needs_context(self):
        self.check_bad("xs ← []", "empty list needs an explicit element type")
        self.check_ok("xs ∈ list[int] ← []")

    def test_membership_relation_also_checks_container_membership(self):
        self.check_ok("xs ← [1, 2, 3]\nx ← 2\nfound ← x ∈ xs")
        self.check_ok("xs ← [1, 2, 3]\nx ← 2\nfound ← xs ∋ x")

    def test_explicit_foreign_scene_class(self):
        self.check_ok(
            "from manimlib import Scene, Circle\n"
            "class Demo(Scene):\n"
            "    def construct(self ∈ Demo) → None:\n"
            "        circle ∈ Circle ← Circle()\n"
            "        self.add(circle)\n"
        )

    def test_scene_method_requires_typed_self(self):
        self.check_bad(
            "from manimlib import Scene\n"
            "class Demo(Scene):\n"
            "    def construct(self) → None:\n"
            "        pass\n",
            "parameter 'self' needs a static type",
        )

    def test_foreign_constructor_result_needs_explicit_type(self):
        self.check_bad(
            "from manimlib import Scene, Circle\n"
            "class Demo(Scene):\n"
            "    def construct(self ∈ Demo) → None:\n"
            "        circle ← Circle()\n",
            "cannot infer assignment type",
        )

    def test_typed_rate_function_expression(self):
        self.check_ok(
            "def reflect(value ∈ float) → float:\n"
            "    return -value if value < 0.0 else value\n"
        )

    def test_comparison_requires_compatible_types(self):
        self.check_bad(
            "def before(value ∈ float) → bool:\n"
            "    return value < 'zero'\n",
            "comparison is not statically defined for float and str",
        )

    def test_conditional_expression_requires_boolean_condition(self):
        self.check_bad(
            "def reflect(value ∈ float) → float:\n"
            "    return -value if value else value\n",
            "expected bool, got float",
        )

    def test_conditional_expression_checks_both_results(self):
        self.check_bad(
            "def label(value ∈ float) → float:\n"
            "    return -value if value < 0.0 else 'positive'\n",
            "expected float, got float | str",
        )


if __name__ == "__main__":
    unittest.main()
