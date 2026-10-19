# Checked NumPy array boundary

An explicitly imported `numpy.ndarray` can be used in Ithon signatures and
bindings. Aliases are resolved through the actual NumPy import; another module
named `np` does not acquire these rules.

The checker recognizes numeric array arithmetic, comparisons, transpose,
integer size metadata and integer shape coordinates. Index expressions are
checked, including tuple and slice components. An indexed foreign result is
unknown until its next explicit typed binding. Dtype, rank, broadcasting and
shape compatibility remain NumPy runtime checks. This is not a dependent array
type or a promise that arbitrary NumPy calls are statically verified.

The conversation-training consumer explicitly casts numerical buffers and
checks shapes, finiteness and precision configuration at its runtime boundary.
This narrow interface enables that consumer without disabling mandatory static
checking for ordinary Ithon code.

The exact-head host qualifier requires all 46 current control, loader and NumPy
tests with zero skips. The native interpreter job is separate: its configure
and build stages receive the qualified absolute ICK compiler explicitly; a
compiler failure does not trigger an ambient cc retry. Both jobs check out the
explicit PR head. The host Python implementation substrate remains foreign;
this change does not claim native tokenizer or physical-device acceptance from
the host qualifier.
