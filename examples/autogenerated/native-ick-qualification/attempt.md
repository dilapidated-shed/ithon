# Native Ithon through the declared ICK stage

Purpose: qualify the actual interpreter and its native language/loader tests,
separately from the passing 46-group host-control/NumPy qualifier. This is the
inherited Ithon implementation substrate, not permission for consumer Python.

Type sketch: the producer resolves one absolute qualified compiler; configure
and every compile/link recipe must consume that producer and its declared
runtime flags. Native execution must use the resulting interpreter. A shared
link failure is a failed native stage, not a host-test success.

Actual first head bf2e4f8b57bde5a9ec7d15184e8f29186a6eabb5 qualified
ICK c61e448251744a2f40ad743ebef1a027bdcd2f9d and compiled the interpreter.
Run 39344697173, job 118374373538 then failed at Modules/array linking:
the linker could not find libatomic_asneeded. The observed shared-link command
used the exact ICK path but omitted CFLAGS. This is not a compiler substitution
or an accepted native test. Host control/NumPy checks passed separately.

The repair supplies -fno-link-libatomic and -static-libgcc through LDFLAGS as
well as CFLAGS, retaining the same compiler, extension set and assertions.
Current native build/execution must pass before merge. The separate successful
producer job retains its exact runtime-keyed cache; the interpreter job still
restores and requalifies the same immutable compiler. No failing consumer gate
is hidden by the producer's success. Physical devices remain NOT_RUN.
