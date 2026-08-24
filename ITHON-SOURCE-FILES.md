# Ithon source files

Ithon source uses `.pi`.

Python source uses `.py`.

This supersedes the earlier experiments that used `.ithon` for strict modules or kept Ithon source in `.py` files and selected the language only by interpreter.

## File and import convention

- `program.pi` is Ithon source.
- `module.pi` is an importable Ithon module.
- `package/__init__.pi` is an Ithon package initializer.
- `.pi` source is parsed with Ithon syntax and checked by Ithon's mandatory static type system before execution.
- `.py` remains ordinary/foreign Python and is loaded through the normal Python import machinery.
- When Ithon resolves an import, an applicable `.pi` module/package is an Ithon module; Python libraries remain available as foreign `.py` dependencies.
- Values crossing from foreign Python into Ithon need statically knowable interfaces or explicit typed boundaries.

The normal command-line spelling is:

```sh
./ithon program.pi
```

Installed scripts may use:

```text
#!/usr/bin/env ithon
```

The extension is part of the language boundary: `.pi` means Ithon and `.py` means Python.
