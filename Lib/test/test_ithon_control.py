"""Compiler-substrate regressions for checked control programs."""
import unittest
from ithon_frontend import check_source, StaticTypeError


class ControlTests(unittest.TestCase):
    def test_recovery_cleanup_loop_and_mapping(self):
        check_source("""from builtins import ValueError
import pathlib
result ∈ dict[str, int] ← {"attempt": 1}
try:
    while result["attempt"] < 3:
        result["attempt"] ← result["attempt"] + 1
        if result["attempt"] == 2:
            continue
        break
except ValueError as failure:
    raise ValueError("invalid") from failure
finally:
    with pathlib.Path(__file__).open("rb") as stream:
        data ∈ bytes ← stream.read()
assert len(data) > 0
""")

    def test_all_branches_are_checked_before_execution(self):
        for body in (
            "try:\n    x ∈ int ← 'bad'\nexcept ValueError:\n    pass",
            "try:\n    pass\nfinally:\n    x ∈ int ← 'bad'",
            "while False:\n    x ∈ int ← 'bad'",
            "with Path('x').open() as stream:\n    x ∈ int ← 'bad'",
        ):
            with self.subTest(body=body), self.assertRaises(StaticTypeError):
                check_source("from builtins import ValueError\nfrom pathlib import Path\n" + body)

    def test_mapping_keys_and_values_are_checked(self):
        for code in (
            "values ∈ dict[str, int] ← {'a': 'bad'}",
            "values ∈ dict[str, int] ← {'a': 1}\nx ← values[1]",
            "values ∈ dict[str, int] ← {'a': 1}\nvalues['a'] ← 'bad'",
            "values ∈ dict[str, int] ← {'a': 1}\nvalues[1] ← 2",
            "values ← {}",
        ):
            with self.subTest(code=code), self.assertRaises(StaticTypeError):
                check_source(code)

    def test_sequence_shape_and_foreign_keywords(self):
        check_source("items ∈ list[int] ← [1, 2]\nx ← items[0]\ny ← items[:1]")
        check_source("pair ← ('a', 1)\nx ∈ str ← pair[0]\ny ∈ int ← pair[1]")
        for code in ("items ← [1]\nx ← items['bad']", "pair ← (1,)\nx ← pair[2]",
                     "import subprocess\nsubprocess.run([], timeout=undeclared)"):
            with self.subTest(code=code), self.assertRaises(StaticTypeError):
                check_source(code)


if __name__ == '__main__':
    unittest.main()
