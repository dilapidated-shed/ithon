"""Strict Ithon runner and .pi module loader."""

from __future__ import annotations

import __future__
import importlib.abc
import importlib.util
import os
import sys
import traceback
from pathlib import Path

from ithon_frontend import StaticTypeError, check_source


class IthonSourceLoader(importlib.abc.SourceLoader):
    def __init__(self, fullname: str, path: str) -> None:
        self.fullname = fullname
        self.path = path

    def get_filename(self, fullname: str) -> str:
        return self.path

    def get_data(self, path: str) -> bytes:
        with open(path, "rb") as handle:
            return handle.read()

    def source_to_code(
        self,
        data: bytes,
        path: str,
        fullname: str | None = None,
        *,
        _optimize: int = -1,
    ):
        source = data.decode("utf-8")
        tree = check_source(source, path)
        return compile(
            tree,
            path,
            "exec",
            flags=__future__.annotations.compiler_flag,
            dont_inherit=True,
            optimize=_optimize,
        )


class IthonFinder(importlib.abc.MetaPathFinder):
    """Find .pi modules while leaving .py to ordinary Python import machinery."""

    def find_spec(self, fullname: str, path=None, target=None):
        search = sys.path if path is None else path
        leaf = fullname.rpartition(".")[2]
        for entry in search:
            base = Path(entry or os.getcwd())
            module = base / f"{leaf}.pi"
            if module.is_file():
                loader = IthonSourceLoader(fullname, str(module))
                return importlib.util.spec_from_file_location(fullname, module, loader=loader)
            package = base / leaf / "__init__.pi"
            if package.is_file():
                loader = IthonSourceLoader(fullname, str(package))
                return importlib.util.spec_from_file_location(
                    fullname,
                    package,
                    loader=loader,
                    submodule_search_locations=[str(package.parent)],
                )
        return None


def _install_importer() -> None:
    if not any(isinstance(finder, IthonFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, IthonFinder())


def _run_source(source: str, filename: str, argv: list[str]) -> None:
    # Check the complete module before executing any top-level statement.
    tree = check_source(source, filename)
    code = compile(
        tree,
        filename,
        "exec",
        flags=__future__.annotations.compiler_flag,
        dont_inherit=True,
    )
    sys.argv = argv
    if filename not in {"<string>", "<stdin>"}:
        sys.path[0] = os.path.dirname(os.path.abspath(filename))
    namespace = {
        "__name__": "__main__",
        "__file__": filename,
        "__package__": None,
        "__cached__": None,
        "__builtins__": __builtins__,
    }
    exec(code, namespace, namespace)


def main(argv: list[str] | None = None) -> None:
    _install_importer()
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit("ithon: interactive mode is not implemented; give a .pi file or -c program")
    if args[0] == "-c":
        if len(args) < 2:
            raise SystemExit("ithon: -c requires an argument")
        _run_source(args[1], "<string>", ["-c", *args[2:]])
        return
    if args[0].startswith("-"):
        raise SystemExit(f"ithon: {args[0]} is not supported yet")
    path = args[0]
    if Path(path).suffix != ".pi":
        raise SystemExit("ithon: Ithon source files use .pi; .py is Python")
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    _run_source(source, path, [path, *args[1:]])


if __name__ == "__main__":
    try:
        main()
    except StaticTypeError as exc:
        sys.stderr.writelines(traceback.format_exception_only(exc))
        raise SystemExit(1) from None
