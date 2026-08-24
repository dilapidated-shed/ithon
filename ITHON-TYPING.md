# Ithon mandatory static typing

Ithon is statically typed. Static typing is not an optional lint mode layered on top of a dynamically typed language.

The initial implementation may reuse CPython's AST, runtime, and object model, but an Ithon module must be statically checked as a complete module before any of its code executes.

## Membership syntax

Ithon uses ordinary membership symbols for typing. There is no separate surface relation for “has type” and no exposed kind relation.

```pi
x ∈ int ← 42
int ∋ x ← 42
42 → x ∈ int
42 → int ∋ x
```

Those four forms express the same typed binding with the two independent relations reversed: `∈`/`∋` reverse membership, and `←`/`→` reverse assignment.

Function parameters use the same membership relation:

```pi
def double(x ∈ int) → int:
    return x × 2

def triple(int ∋ x) → int:
    return x × 3
```

`x: int` is not Ithon type syntax. Internally the current frontend may lower membership syntax to CPython AST annotation nodes; that is an implementation detail, not accepted Ithon notation.

The same `∈`/`∋` relation is also used for ordinary membership expressions:

```pi
found ← x ∈ xs
found ← xs ∋ x
```

## Core rules

- There is no implicit `Any`.
- An assignment with an unambiguous value may infer its type.
- Once a name has a static type, later assignment must preserve that type.
- An explicit membership type must match the assigned value.
- Numeric widening may be accepted where the target type explicitly permits it, for example assigning an integer value to a `float` binding.
- Function parameters require static types.
- Function results require static types. `__init__` may infer `None` as its result.
- Function bodies and local calls are checked against those signatures.
- Lambda parameters may be inferred from an explicit contextual `Callable[[...], result]` type. A lambda without enough contextual type information is rejected rather than silently becoming dynamic.
- Empty containers require enough context to determine their element/key/value types.
- Imports from foreign Python libraries do not silently inject dynamic values into Ithon. If the checker cannot determine a foreign result's type, the Ithon binding needs an explicit type boundary.
- Star imports are rejected when they make bindings statically unknowable.
- Unsupported constructs fail as unsupported static typing rather than quietly falling back to dynamic execution.

Representative intended behavior:

```pi
x ← 42
x ← 43                         # accepted
x ← "forty two"                # rejected

x ∈ float ← 42                 # accepted
x ∈ int ← 4.2                  # rejected

def double(x ∈ int) → int:
    return x × 2

double("21")                   # rejected

double_fn ∈ Callable[[int], int] ← λ x: x × 2

import math
root ∈ float ← math.sqrt(4.0)
```

The checker should finish checking the entire module before execution begins, so an error later in a file cannot occur after earlier top-level statements have already produced side effects.

## Initial class boundary

Classes are checked rather than treated as a dynamic Python escape. The first
class slice exists to support real Manimi scenes:

```pi
from manimlib import Scene, Circle

class Demo(Scene):
    def construct(self ∈ Demo) → None:
        circle ∈ Circle ← Circle()
        self.add(circle)
```

- A base must be a known local type or an explicit foreign import.
- A method receiver currently states its class membership explicitly.
- A foreign constructor result needs an explicit membership boundary before
  it is bound in Ithon.
- Class decorators, metaclass keywords, and inferred instance attributes are
  not part of this first slice; they fail as unsupported instead of falling
  back to dynamic checking.

## Relation to Python

Python is an implementation and library substrate, not a syntax-compatibility target. Ordinary `.py` source is foreign Python. Ithon source uses `.pi`; that naming decision is tracked independently on `feature/pi-source-files`.

The CPython tree is an implementation substrate and source/reference pool. Ithon changes do not need to be structured as patches suitable for acceptance by Python upstream.

## Later type-system work

Mandatory static typing is the floor, not the ceiling. Refinements, dependent facts, indexed quantities such as `Bits[n]`, proofs about bounds and widths, and representation selection belong to later type-system passes and are tracked separately on `feature/dependent-refinement-types`.
